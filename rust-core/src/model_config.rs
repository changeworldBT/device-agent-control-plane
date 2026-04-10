use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::error::{CoreError, CoreResult};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum ModelRunMode {
    Off,
    Mock,
    Live,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum AgentMode {
    SingleAgent,
    MultiAgent,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ModelProvider {
    pub kind: String,
    #[serde(default)]
    pub base_url_env: Option<String>,
    #[serde(default)]
    pub api_key_env: Option<String>,
    #[serde(default)]
    pub default_model: Option<String>,
    #[serde(default)]
    pub default_model_env: Option<String>,
    #[serde(default)]
    pub capabilities: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct AgentMember {
    #[serde(default)]
    pub provider: Option<String>,
    #[serde(default)]
    pub model: Option<String>,
    #[serde(default)]
    pub model_env: Option<String>,
    #[serde(default)]
    pub roles: Vec<String>,
    #[serde(default)]
    pub system_contract: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct AgentTeamConfig {
    pub mode: AgentMode,
    #[serde(default)]
    pub default_agent: Option<String>,
    #[serde(default)]
    pub role_map: BTreeMap<String, String>,
    pub members: BTreeMap<String, AgentMember>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ModelProviderConfig {
    pub version: u32,
    pub mode: ModelRunMode,
    pub default_provider: String,
    #[serde(default)]
    pub active_provider: Option<String>,
    pub providers: BTreeMap<String, ModelProvider>,
    pub agents: AgentTeamConfig,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ModelRoute {
    pub mode: ModelRunMode,
    pub agent_mode: AgentMode,
    pub role: String,
    pub agent_id: String,
    pub provider_name: String,
    pub provider_kind: String,
    pub model: Option<String>,
    pub model_env: Option<String>,
    pub base_url_env: Option<String>,
    pub api_key_env: Option<String>,
    pub capabilities: Vec<String>,
    pub system_contract: Option<String>,
}

pub fn load_model_config_json(raw: &str) -> CoreResult<ModelProviderConfig> {
    let config: ModelProviderConfig =
        serde_json::from_str(raw).map_err(|error| CoreError::Serialization(error.to_string()))?;
    config.validate()?;
    Ok(config)
}

impl ModelProviderConfig {
    pub fn validate(&self) -> CoreResult<()> {
        if self.version == 0 {
            return invalid_config("version must be at least 1");
        }
        if self.providers.is_empty() {
            return invalid_config("providers must not be empty");
        }
        if !self.providers.contains_key(&self.default_provider) {
            return invalid_config(format!(
                "default_provider references unknown provider: {}",
                self.default_provider
            ));
        }
        if let Some(active_provider) = &self.active_provider {
            if !self.providers.contains_key(active_provider) {
                return invalid_config(format!(
                    "active_provider references unknown provider: {active_provider}"
                ));
            }
        }
        if self.agents.members.is_empty() {
            return invalid_config("agents.members must not be empty");
        }
        if let Some(default_agent) = &self.agents.default_agent {
            if !self.agents.members.contains_key(default_agent) {
                return invalid_config(format!(
                    "default_agent references unknown agent: {default_agent}"
                ));
            }
        }
        for (role, agent_id) in &self.agents.role_map {
            if !self.agents.members.contains_key(agent_id) {
                return invalid_config(format!("role {role} references unknown agent: {agent_id}"));
            }
        }
        for (agent_id, member) in &self.agents.members {
            if let Some(provider_name) = &member.provider {
                if !self.providers.contains_key(provider_name) {
                    return invalid_config(format!(
                        "agent {agent_id} references unknown provider: {provider_name}"
                    ));
                }
            }
        }
        Ok(())
    }

    pub fn resolve_route(
        &self,
        role: &str,
        provider_override: Option<&str>,
        agent_override: Option<&str>,
    ) -> CoreResult<ModelRoute> {
        self.validate()?;
        let agent_id = self.select_agent_id(role, agent_override)?;
        let agent = self.agents.members.get(&agent_id).ok_or_else(|| {
            CoreError::InvalidConfiguration(format!("agent not found: {agent_id}"))
        })?;
        let provider_name = self.select_provider_name(agent, provider_override)?;
        let provider = self.providers.get(&provider_name).ok_or_else(|| {
            CoreError::InvalidConfiguration(format!("provider not found: {provider_name}"))
        })?;
        let model_env = agent
            .model_env
            .clone()
            .or_else(|| provider.default_model_env.clone());
        let model = agent
            .model
            .clone()
            .or_else(|| provider.default_model.clone());

        Ok(ModelRoute {
            mode: self.mode.clone(),
            agent_mode: self.agents.mode.clone(),
            role: role.to_owned(),
            agent_id,
            provider_name,
            provider_kind: provider.kind.clone(),
            model,
            model_env,
            base_url_env: provider.base_url_env.clone(),
            api_key_env: provider.api_key_env.clone(),
            capabilities: provider.capabilities.clone(),
            system_contract: agent.system_contract.clone(),
        })
    }

    fn select_agent_id(&self, role: &str, agent_override: Option<&str>) -> CoreResult<String> {
        if let Some(agent_id) = clean(agent_override) {
            if self.agents.members.contains_key(agent_id) {
                return Ok(agent_id.to_owned());
            }
            return invalid_config(format!(
                "agent override references unknown agent: {agent_id}"
            ));
        }

        if self.agents.mode == AgentMode::MultiAgent {
            if let Some(agent_id) = self.agents.role_map.get(role) {
                return Ok(agent_id.clone());
            }
        }

        if let Some(agent_id) = &self.agents.default_agent {
            return Ok(agent_id.clone());
        }

        self.agents.members.keys().next().cloned().ok_or_else(|| {
            CoreError::InvalidConfiguration("agents.members must not be empty".to_owned())
        })
    }

    fn select_provider_name(
        &self,
        agent: &AgentMember,
        provider_override: Option<&str>,
    ) -> CoreResult<String> {
        if let Some(provider_name) = clean(provider_override) {
            if self.providers.contains_key(provider_name) {
                return Ok(provider_name.to_owned());
            }
            return invalid_config(format!(
                "provider override references unknown provider: {provider_name}"
            ));
        }

        let provider_name = agent
            .provider
            .as_deref()
            .or(self.active_provider.as_deref())
            .unwrap_or(&self.default_provider);
        if self.providers.contains_key(provider_name) {
            return Ok(provider_name.to_owned());
        }
        invalid_config(format!("provider reference is unknown: {provider_name}"))
    }
}

fn clean(value: Option<&str>) -> Option<&str> {
    value.map(str::trim).filter(|value| !value.is_empty())
}

fn invalid_config<T>(message: impl Into<String>) -> CoreResult<T> {
    Err(CoreError::InvalidConfiguration(message.into()))
}
