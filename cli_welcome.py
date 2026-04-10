from __future__ import annotations


GOLD = "\x1b[38;5;220m"
AMBER = "\x1b[38;5;214m"
DIM = "\x1b[2m"
RESET = "\x1b[0m"

DRAGON = r"""
                       / \  //\
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
                   \\\\_/.-~     ~
"""


def render_welcome(*, color: bool = True) -> str:
    art = DRAGON.strip("\n")
    title = "DEVICE AGENT CONTROL PLANE"
    subtitle = "golden dragon console | local-first execution core"
    commands = "try: run_replays.py | run_local_crm_scenario.py | run_http_crm_scenario.py"

    if not color:
        return f"{art}\n\n{title}\n{subtitle}\n{commands}"

    return "\n".join(
        [
            f"{GOLD}{art}{RESET}",
            "",
            f"{AMBER}{title}{RESET}",
            f"{DIM}{subtitle}{RESET}",
            f"{DIM}{commands}{RESET}",
        ]
    )
