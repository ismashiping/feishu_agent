"""Offline public contract demo; no runtime resources."""
from pydantic import ValidationError
from clinical_agent.api.schemas import QuestionBody

if __name__ == "__main__":
    request = QuestionBody(question="What are the limitations?", scope="online")
    print("accepted scope:", request.scope)
    try:
        QuestionBody(question="test", scope="local")
    except ValidationError:
        print("retired scope rejected before runtime")
    else:
        raise AssertionError("Retired scope was accepted")
