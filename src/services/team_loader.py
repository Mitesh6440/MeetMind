from pathlib import Path
import json

from pydantic import ValidationError

from models.team import Team, TeamMember


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


def save_team_to_json(team: Team, path: Path | None = None) -> Path:
    """
    Save team data to a JSON file.
    
    Returns:
        Path to the saved file.
    """
    path = path or DEFAULT_TEAM_JSON
    
    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Convert to dict and save
        data = team.model_dump()
        path.write_text(
            json.dumps(data, indent=4, ensure_ascii=False),
            encoding="utf-8"
        )
        return path
    except Exception as e:
        raise TeamDataError(f"Failed to save team JSON: {e}")


def add_team_member(member: TeamMember, path: Path | None = None) -> Team:
    """
    Add a new team member to the team.
    
    Returns:
        Updated Team object.
    """
    team = load_team_from_json(path)
    
    # Check if member with same name already exists
    if any(m.name.lower() == member.name.lower() for m in team.members):
        raise TeamDataError(f"Team member with name '{member.name}' already exists")
    
    team.members.append(member)
    save_team_to_json(team, path)
    return team


def update_team_member(member_name: str, updated_member: TeamMember, path: Path | None = None) -> Team:
    """
    Update an existing team member.
    
    Args:
        member_name: Current name of the member to update
        updated_member: Updated member data
        path: Optional path to team JSON file
        
    Returns:
        Updated Team object.
    """
    team = load_team_from_json(path)
    
    # Find and update member
    found = False
    for i, member in enumerate(team.members):
        if member.name.lower() == member_name.lower():
            team.members[i] = updated_member
            found = True
            break
    
    if not found:
        raise TeamDataError(f"Team member '{member_name}' not found")
    
    save_team_to_json(team, path)
    return team


def delete_team_member(member_name: str, path: Path | None = None) -> Team:
    """
    Delete a team member.
    
    Returns:
        Updated Team object.
    """
    team = load_team_from_json(path)
    
    # Check if at least one member will remain
    if len(team.members) <= 1:
        raise TeamDataError("Cannot delete the last team member. Team must have at least one member.")
    
    # Remove member
    original_count = len(team.members)
    team.members = [m for m in team.members if m.name.lower() != member_name.lower()]
    
    if len(team.members) == original_count:
        raise TeamDataError(f"Team member '{member_name}' not found")
    
    save_team_to_json(team, path)
    return team