# logging.basicConfig(level=logging.DEBUG)


import openai
from pyinstrument import Profiler

import agentops


def make_openai_call():
    client = openai.Client()
    return client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a chatbot."},
            {"role": "user", "content": "What are you talking about?"},
        ],
    )


# Initialize profiler
profiler = Profiler()
profiler.start()

try:
    # Initialize AgentOps with auto_start_session=False
    agentops.init(auto_start_session=False)
    # Start a single test session
    session = agentops.start_session()
    assert session is not None

    # Make multiple calls
    responses = []
    # Make 20 sequential calls for benchmarking
    for _ in range(1):
        responses.append(make_openai_call())

    # End the session properly
    session.end_session(end_state="Success")

finally:
    # Stop profiling and print results
    profiler.stop()
    # with open("profiling_reports/{}.txt".format(datetime.now(timezone.utc).isoformat()), "w") as f:
    #     f.write(profiler.output_text(unicode=True, color=False))
    print(profiler.output_text(unicode=True, color=True))
