// API Configuration
const API_BASE_URL = 'http://localhost:8000'; // Change this to your backend URL

// API Helper Functions
class API {
    static async uploadAudio(file) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API_BASE_URL}/api/v1/audio/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }

        return await response.json();
    }

    static async getTeam() {
        const response = await fetch(`${API_BASE_URL}/api/v1/team`);
        
        if (!response.ok) {
            throw new Error('Failed to fetch team');
        }

        return await response.json();
    }

    static async validateTasks(tasks) {
        const response = await fetch(`${API_BASE_URL}/api/v1/tasks/validate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(tasks)
        });

        if (!response.ok) {
            throw new Error('Validation failed');
        }

        return await response.json();
    }

    static async addTeamMember(member) {
        const response = await fetch(`${API_BASE_URL}/api/v1/team/members`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(member)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to add team member');
        }

        return await response.json();
    }

    static async updateTeamMember(memberName, updatedMember) {
        const response = await fetch(`${API_BASE_URL}/api/v1/team/members/${encodeURIComponent(memberName)}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updatedMember)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to update team member');
        }

        return await response.json();
    }

    static async deleteTeamMember(memberName) {
        const response = await fetch(`${API_BASE_URL}/api/v1/team/members/${encodeURIComponent(memberName)}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete team member');
        }

        return await response.json();
    }

    static async updateTeam(team) {
        const response = await fetch(`${API_BASE_URL}/api/v1/team`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(team)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to update team');
        }

        return await response.json();
    }
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = API;
}

