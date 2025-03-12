from termcolor import colored


DASHBOARD_URL = "https://app.agentops.com"





def log_startup_message(self):
    """Log a startup message."""
    project_id = ""  # TODO
    dashboard_url = f"{DASHBOARD_URL}/{project_id}"
    logger.info(
        colored(
            f"\x1b[34mSession Replay: {dashboard_url}\x1b[0m",
            "blue",
        )
    )


def log_shutdown_message(self):
    """Log a shutdown message."""
    if analytics_stats := self.get_analytics():
        analytics = (
            f"Session Stats - "
            f"{colored('Duration:', attrs=['bold'])} {analytics_stats['Duration']} | "
            f"{colored('Cost:', attrs=['bold'])} ${analytics_stats['Cost']} | "
            f"{colored('LLMs:', attrs=['bold'])} {analytics_stats['LLM calls']} | "
            f"{colored('Tools:', attrs=['bold'])} {analytics_stats['Tool calls']} | "
            f"{colored('Actions:', attrs=['bold'])} {analytics_stats['Actions']} | "
            f"{colored('Errors:', attrs=['bold'])} {analytics_stats['Errors']}"
        )
        logger.info(analytics)


def _get_analytics(project_id: str) -> dict:
    """Get analytics for the project."""
    pass