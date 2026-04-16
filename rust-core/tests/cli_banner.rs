use device_agent_core::render_welcome;

#[test]
fn welcome_renders_golden_dragon_banner() {
    let rendered = render_welcome(false);

    assert!(rendered.contains("金色中国龙"));
    assert!(rendered.contains("(@::@)"));
    assert!(rendered.contains("DEVICE AGENT CONTROL PLANE"));
    assert!(rendered.contains("金色中国龙 console"));
    assert!(!rendered.contains("\x1b["));
}

#[test]
fn welcome_can_render_with_ansi_gold() {
    let rendered = render_welcome(true);

    assert!(rendered.contains("\x1b[38;5;220m"));
    assert!(rendered.contains("DEVICE AGENT CONTROL PLANE"));
}
