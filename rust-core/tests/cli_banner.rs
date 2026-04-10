use device_agent_core::render_welcome;

#[test]
fn welcome_renders_golden_dragon_banner() {
    let rendered = render_welcome(false);

    assert!(rendered.contains(r"/0  0  \__"));
    assert!(rendered.contains("DEVICE AGENT CONTROL PLANE"));
    assert!(rendered.contains("golden dragon console"));
    assert!(!rendered.contains("\x1b["));
}

#[test]
fn welcome_can_render_with_ansi_gold() {
    let rendered = render_welcome(true);

    assert!(rendered.contains("\x1b[38;5;220m"));
    assert!(rendered.contains("DEVICE AGENT CONTROL PLANE"));
}
