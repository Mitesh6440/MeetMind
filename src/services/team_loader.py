from pathlib import Path
import json

from pydantic import ValidationError

from models.team import Team


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_TEAM_JSON = BASE_DIR / "data" / "team" / "team_members.json"


class TeamDataError(Exception):
    """Raised when team data is missing or invalid."""
    pass


def load_team_from_json(path: Path | None = None) -> Team:
    """
    Load team data from a JSON file and return a validated Team object.

    JSON format:
    {
      "members": [
        { "name": "...", "role": "...", "skills": ["..."] }
      ]
    }
    """
    path = path or DEFAULT_TEAM_JSON

    if not path.exists():
        raise TeamDataError(f"Team JSON file not found at: {path}")

    try:
        raw_data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise TeamDataError(f"Failed to read/parse team JSON: {e}")

    try:
        team = Team(**raw_data)
    except ValidationError as e:
        raise TeamDataError(f"Team JSON validation failed: {e}")

    return team


# Small wrapper for future flexibility, but currently JSON-only
def load_team() -> Team:
    return load_team_from_json()
