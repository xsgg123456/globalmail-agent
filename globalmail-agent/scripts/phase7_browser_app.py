"""Browser QA only: the test driver advances real scoped runs, without background races."""
from globalmail_agent.main import create_app
from globalmail_agent.settings import Settings

app = create_app(Settings.from_env(), start_worker=False)
