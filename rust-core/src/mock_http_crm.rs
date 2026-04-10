use std::fs;
use std::io::{Read, Write};
use std::net::TcpStream;
use std::path::{Path, PathBuf};
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc, Mutex,
};
use std::thread::{self, JoinHandle};
use std::time::Duration;

use serde_json::{json, Value};
use tiny_http::{Header, Method, Response, Server, StatusCode};

use crate::error::{CoreError, CoreResult};

#[derive(Debug, Clone)]
pub struct MockHttpCrmSnapshot {
    pub crm_record: Value,
    pub outbox: Value,
}

#[derive(Debug)]
struct MockHttpCrmState {
    crm_record: Value,
    outbox: Value,
}

#[derive(Debug)]
pub struct MockHttpCrmServer {
    seed_dir: PathBuf,
    state: Arc<Mutex<MockHttpCrmState>>,
    stop_flag: Arc<AtomicBool>,
    thread: Option<JoinHandle<()>>,
    base_url: String,
}

impl MockHttpCrmServer {
    pub fn new(seed_dir: impl AsRef<Path>) -> CoreResult<Self> {
        let seed_dir = seed_dir.as_ref().to_path_buf();
        let state = Arc::new(Mutex::new(MockHttpCrmState {
            crm_record: read_json(&seed_dir.join("crm_record.json"))?,
            outbox: read_json(&seed_dir.join("outbox.json"))?,
        }));
        let stop_flag = Arc::new(AtomicBool::new(false));
        let server = Server::http("127.0.0.1:0")
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let base_url = format!("http://{}", server.server_addr());
        let state_clone = Arc::clone(&state);
        let stop_clone = Arc::clone(&stop_flag);

        let thread = thread::spawn(move || loop {
            if stop_clone.load(Ordering::SeqCst) {
                break;
            }
            match server.recv_timeout(Duration::from_millis(100)) {
                Ok(Some(request)) => {
                    let _ = handle_request(request, &state_clone);
                }
                Ok(None) => {}
                Err(_) => break,
            }
        });

        Ok(Self {
            seed_dir,
            state,
            stop_flag,
            thread: Some(thread),
            base_url,
        })
    }

    pub fn base_url(&self) -> &str {
        &self.base_url
    }

    pub fn reset(&self) -> CoreResult<()> {
        let mut state = self
            .state
            .lock()
            .map_err(|_| CoreError::Serialization("mock http server mutex poisoned".to_owned()))?;
        state.crm_record = read_json(&self.seed_dir.join("crm_record.json"))?;
        state.outbox = read_json(&self.seed_dir.join("outbox.json"))?;
        Ok(())
    }

    pub fn snapshot(&self) -> CoreResult<MockHttpCrmSnapshot> {
        let state = self
            .state
            .lock()
            .map_err(|_| CoreError::Serialization("mock http server mutex poisoned".to_owned()))?;
        Ok(MockHttpCrmSnapshot {
            crm_record: state.crm_record.clone(),
            outbox: state.outbox.clone(),
        })
    }
}

impl Drop for MockHttpCrmServer {
    fn drop(&mut self) {
        self.stop_flag.store(true, Ordering::SeqCst);
        let _ = send_shutdown_probe(&self.base_url);
        if let Some(thread) = self.thread.take() {
            let _ = thread.join();
        }
    }
}

fn send_shutdown_probe(base_url: &str) -> CoreResult<()> {
    let authority = base_url.strip_prefix("http://").ok_or_else(|| {
        CoreError::Serialization("mock server base URL should be http".to_owned())
    })?;
    let mut stream = TcpStream::connect(authority)
        .map_err(|error| CoreError::Serialization(error.to_string()))?;
    stream
        .write_all(
            format!(
                "GET /__shutdown_probe__ HTTP/1.1\r\nHost: {authority}\r\nConnection: close\r\n\r\n"
            )
            .as_bytes(),
        )
        .map_err(|error| CoreError::Serialization(error.to_string()))
}

fn handle_request(
    mut request: tiny_http::Request,
    state: &Arc<Mutex<MockHttpCrmState>>,
) -> CoreResult<()> {
    if !is_authorized(&request) {
        respond_json(
            request,
            StatusCode(403),
            json!({"error": "missing_grant_context"}),
        )?;
        return Ok(());
    }

    let method = request.method().clone();
    let url = request.url().to_owned();
    match (method, url.as_str()) {
        (Method::Get, "/crm/record") => {
            let snapshot = snapshot_state(state)?;
            respond_json(
                request,
                StatusCode(200),
                json!({ "crm_record": snapshot.crm_record }),
            )?;
        }
        (Method::Get, "/outbox") => {
            let snapshot = snapshot_state(state)?;
            respond_json(
                request,
                StatusCode(200),
                json!({ "outbox": snapshot.outbox }),
            )?;
        }
        (Method::Patch, "/crm/status") => {
            let payload = read_request_json(request.as_reader())?;
            let response = {
                let mut locked = state.lock().map_err(|_| {
                    CoreError::Serialization("mock http server mutex poisoned".to_owned())
                })?;
                locked.crm_record["renewal_status"] = payload["renewal_status"].clone();
                locked.crm_record["history"]
                    .as_array_mut()
                    .ok_or_else(|| CoreError::Serialization("crm history should be array".to_owned()))?
                    .push(json!({
                        "at": payload["at"],
                        "event": payload.get("event").cloned().unwrap_or_else(|| json!("status updated"))
                    }));
                json!({ "crm_record": locked.crm_record.clone() })
            };
            respond_json(request, StatusCode(200), response)?;
        }
        (Method::Post, "/messages/send") => {
            let payload = read_request_json(request.as_reader())?;
            let response = {
                let mut locked = state.lock().map_err(|_| {
                    CoreError::Serialization("mock http server mutex poisoned".to_owned())
                })?;
                locked
                    .outbox
                    .as_array_mut()
                    .ok_or_else(|| CoreError::Serialization("outbox should be array".to_owned()))?
                    .push(payload.clone());
                locked.crm_record["renewal_status"] = json!("follow_up_sent");
                locked.crm_record["last_follow_up_at"] = payload["sent_at"].clone();
                locked.crm_record["history"]
                    .as_array_mut()
                    .ok_or_else(|| {
                        CoreError::Serialization("crm history should be array".to_owned())
                    })?
                    .push(json!({"at": payload["sent_at"], "event": "follow-up email sent"}));
                json!({
                    "message": payload,
                    "crm_record": locked.crm_record.clone(),
                    "outbox_entries": locked.outbox.as_array().map(|items| items.len()).unwrap_or(0),
                })
            };
            respond_json(request, StatusCode(200), response)?;
        }
        (Method::Post, "/messages/correction") => {
            let payload = read_request_json(request.as_reader())?;
            let response = {
                let mut locked = state.lock().map_err(|_| {
                    CoreError::Serialization("mock http server mutex poisoned".to_owned())
                })?;
                locked
                    .outbox
                    .as_array_mut()
                    .ok_or_else(|| CoreError::Serialization("outbox should be array".to_owned()))?
                    .push(payload.clone());
                locked.crm_record["last_compensation_at"] = payload["sent_at"].clone();
                locked.crm_record["history"]
                    .as_array_mut()
                    .ok_or_else(|| {
                        CoreError::Serialization("crm history should be array".to_owned())
                    })?
                    .push(
                        json!({"at": payload["sent_at"], "event": "compensation correction sent"}),
                    );
                json!({
                    "message": payload,
                    "crm_record": locked.crm_record.clone(),
                    "outbox_entries": locked.outbox.as_array().map(|items| items.len()).unwrap_or(0),
                })
            };
            respond_json(request, StatusCode(200), response)?;
        }
        (Method::Post, "/crm/restore-status") => {
            let payload = read_request_json(request.as_reader())?;
            let response = {
                let mut locked = state.lock().map_err(|_| {
                    CoreError::Serialization("mock http server mutex poisoned".to_owned())
                })?;
                locked.crm_record["renewal_status"] = payload["renewal_status"].clone();
                locked.crm_record["history"]
                    .as_array_mut()
                    .ok_or_else(|| CoreError::Serialization("crm history should be array".to_owned()))?
                    .push(json!({"at": payload["restored_at"], "event": "status restored by compensation path"}));
                json!({ "crm_record": locked.crm_record.clone() })
            };
            respond_json(request, StatusCode(200), response)?;
        }
        _ => {
            respond_json(request, StatusCode(404), json!({"error": "not_found"}))?;
        }
    }
    Ok(())
}

fn is_authorized(request: &tiny_http::Request) -> bool {
    if request.url() == "/__shutdown_probe__" {
        return true;
    }
    let has_grant = request
        .headers()
        .iter()
        .any(|header| header.field.equiv("X-Grant-Id"));
    let has_principal = request
        .headers()
        .iter()
        .any(|header| header.field.equiv("X-Principal-Ref"));
    has_grant && has_principal
}

fn read_request_json<T: Read>(mut reader: T) -> CoreResult<Value> {
    let mut body = String::new();
    reader
        .read_to_string(&mut body)
        .map_err(|error| CoreError::Serialization(error.to_string()))?;
    if body.trim().is_empty() {
        return Ok(json!({}));
    }
    serde_json::from_str(&body).map_err(|error| CoreError::Serialization(error.to_string()))
}

fn respond_json(request: tiny_http::Request, status: StatusCode, payload: Value) -> CoreResult<()> {
    let body = serde_json::to_string_pretty(&payload)
        .map_err(|error| CoreError::Serialization(error.to_string()))?;
    let response = Response::from_string(body)
        .with_status_code(status)
        .with_header(
            Header::from_bytes("Content-Type", "application/json; charset=utf-8")
                .map_err(|_| CoreError::Serialization("invalid content-type header".to_owned()))?,
        );
    request
        .respond(response)
        .map_err(|error| CoreError::Serialization(error.to_string()))?;
    Ok(())
}

fn snapshot_state(state: &Arc<Mutex<MockHttpCrmState>>) -> CoreResult<MockHttpCrmSnapshot> {
    let locked = state
        .lock()
        .map_err(|_| CoreError::Serialization("mock http server mutex poisoned".to_owned()))?;
    Ok(MockHttpCrmSnapshot {
        crm_record: locked.crm_record.clone(),
        outbox: locked.outbox.clone(),
    })
}

fn read_json(path: &Path) -> CoreResult<Value> {
    let raw =
        fs::read_to_string(path).map_err(|error| CoreError::Serialization(error.to_string()))?;
    serde_json::from_str(&raw).map_err(|error| CoreError::Serialization(error.to_string()))
}
