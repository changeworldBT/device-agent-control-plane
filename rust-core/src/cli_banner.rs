const GOLD: &str = "\x1b[38;5;220m";
const AMBER: &str = "\x1b[38;5;214m";
const DIM: &str = "\x1b[2m";
const RESET: &str = "\x1b[0m";

const DRAGON: &str = r#"                       / \  //\
          |\___/|     /   \//  \\
          /0  0  \__ /    //  | \ \
         /     /  \/_    //   |  \  \
         @_^_@'    \/_  //    |   \   \
           V|       \/_//     |    \    \
            |        \///     |     \     \
            |  ___   //       |      \     \
           _| /   \ //        |       \     \
         _/ _/     //         |        \    _\
        / _/      //          |         \.-~  \
     .-~_/       ((          _|             _  )
    /.-~          \\    .-~ _ _  _ _ _ .-~` `~
                   \\\\_/.-~     ~"#;

pub fn render_welcome(color: bool) -> String {
    let title = "DEVICE AGENT CONTROL PLANE";
    let subtitle = "golden dragon console | local-first execution core";
    let commands = "try: run_replays.py | run_local_crm_scenario.py | run_http_crm_scenario.py";

    if !color {
        return format!("{DRAGON}\n\n{title}\n{subtitle}\n{commands}");
    }

    format!("{GOLD}{DRAGON}{RESET}\n\n{AMBER}{title}{RESET}\n{DIM}{subtitle}{RESET}\n{DIM}{commands}{RESET}")
}
