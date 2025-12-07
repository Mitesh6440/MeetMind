// Team Management
let editingMemberName = null;

// Show team management section
function showTeamManagement() {
    // Hide all other sections
    const uploadSection = document.getElementById('uploadSection');
    const resultsSection = document.getElementById('resultsSection');
    const teamSection = document.getElementById('teamSection');
    
    if (uploadSection) uploadSection.style.display = 'none';
    if (resultsSection) resultsSection.style.display = 'none';
    if (teamSection) teamSection.style.display = 'block';
    
    // Hide back button in header
    const backToUploadBtn = document.getElementById('backToUploadBtn');
    if (backToUploadBtn) {
        backToUploadBtn.style.display = 'none';
    }
    
    // Reset any progress indicators that might be visible
    try {
        if (window.resetProgress && typeof window.resetProgress === 'function') {
            window.resetProgress();
        } else if (typeof resetProgress === 'function') {
            resetProgress();
        }
    } catch (e) {
        // Function might not be loaded yet, that's okay
        console.log('resetProgress not available');
    }
    
    loadTeamMembers();
}

// Hide team management section
function hideTeamManagement() {
    // Hide team section
    document.getElementById('teamSection').style.display = 'none';
    
    // Show upload section
    document.getElementById('uploadSection').style.display = 'block';
    
    // Hide results section (user needs to upload again)
    const resultsSection = document.getElementById('resultsSection');
    if (resultsSection) {
        resultsSection.style.display = 'none';
    }
    
    // Reset progress indicators (call from upload.js if available)
    // This ensures clean state when returning to upload
    try {
        if (window.resetProgress && typeof window.resetProgress === 'function') {
            window.resetProgress();
        } else if (typeof resetProgress === 'function') {
            resetProgress();
        }
    } catch (e) {
        // Function might not be loaded yet, that's okay
        console.log('resetProgress not available yet');
    }
}

// Load and display team members
async function loadTeamMembers() {
    try {
        const team = await API.getTeam();
        displayTeamMembers(team.members);
    } catch (error) {
        console.error('Failed to load team:', error);
        alert('Failed to load team members: ' + error.message);
    }
}

// Display team members
function displayTeamMembers(members) {
    const list = document.getElementById('teamMembersList');
    list.innerHTML = '';

    if (members.length === 0) {
        list.innerHTML = '<p style="text-align: center; color: var(--text-secondary); padding: 2rem;">No team members yet. Add your first team member!</p>';
        return;
    }

    members.forEach(member => {
        const memberCard = createMemberCard(member);
        list.appendChild(memberCard);
    });
}

// Create member card
function createMemberCard(member) {
    const card = document.createElement('div');
    card.className = 'member-card';
    
    card.innerHTML = `
        <div class="member-info">
            <div class="member-name">${escapeHtml(member.name)}</div>
            <div class="member-role">${escapeHtml(member.role)}</div>
            <div class="member-skills">
                ${member.skills.map(skill => `<span class="skill-tag">${escapeHtml(skill)}</span>`).join('')}
            </div>
        </div>
        <div class="member-actions">
            <button class="btn btn-small btn-secondary" onclick="editMember('${escapeHtml(member.name)}')">Edit</button>
            <button class="btn btn-small" style="background-color: var(--danger-color); color: white;" onclick="deleteMember('${escapeHtml(member.name)}')">Delete</button>
        </div>
    `;

    return card;
}

// Show add member form
function showAddMemberForm() {
    editingMemberName = null;
    document.getElementById('memberFormTitle').textContent = 'Add Team Member';
    document.getElementById('memberFormElement').reset();
    document.getElementById('memberForm').style.display = 'block';
    document.getElementById('memberForm').scrollIntoView({ behavior: 'smooth' });
}

// Show edit member form
async function editMember(memberName) {
    try {
        const team = await API.getTeam();
        const member = team.members.find(m => m.name === memberName);
        
        if (!member) {
            alert('Member not found');
            return;
        }

        editingMemberName = memberName;
        document.getElementById('memberFormTitle').textContent = 'Edit Team Member';
        document.getElementById('memberName').value = member.name;
        document.getElementById('memberRole').value = member.role;
        document.getElementById('memberSkills').value = member.skills.join(', ');
        document.getElementById('memberForm').style.display = 'block';
        document.getElementById('memberForm').scrollIntoView({ behavior: 'smooth' });
    } catch (error) {
        console.error('Failed to load member:', error);
        alert('Failed to load member: ' + error.message);
    }
}

// Hide member form
function hideMemberForm() {
    document.getElementById('memberForm').style.display = 'none';
    editingMemberName = null;
}

// Handle member form submit
async function handleMemberSubmit(event) {
    event.preventDefault();

    const name = document.getElementById('memberName').value.trim();
    const role = document.getElementById('memberRole').value.trim();
    const skillsInput = document.getElementById('memberSkills').value.trim();
    
    // Parse skills (comma-separated)
    const skills = skillsInput.split(',')
        .map(s => s.trim())
        .filter(s => s.length > 0);

    if (skills.length === 0) {
        alert('Please provide at least one skill');
        return;
    }

    const member = {
        name: name,
        role: role,
        skills: skills
    };

    try {
        if (editingMemberName) {
            // Update existing member
            await API.updateTeamMember(editingMemberName, member);
            alert('Team member updated successfully!');
        } else {
            // Add new member
            await API.addTeamMember(member);
            alert('Team member added successfully!');
        }

        hideMemberForm();
        loadTeamMembers();
        // Reload team members in tasks.js for filters
        if (typeof loadTeamMembers === 'function' && document.getElementById('filterAssignee')) {
            // Reload assignee filter
            const assigneeFilter = document.getElementById('filterAssignee');
            assigneeFilter.innerHTML = '<option value="all">All</option>';
            const team = await API.getTeam();
            team.members.forEach(m => {
                const option = document.createElement('option');
                option.value = m.name;
                option.textContent = m.name;
                assigneeFilter.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Failed to save member:', error);
        alert('Error: ' + error.message);
    }
}

// Delete member
async function deleteMember(memberName) {
    if (!confirm(`Are you sure you want to delete "${memberName}"?`)) {
        return;
    }

    try {
        await API.deleteTeamMember(memberName);
        alert('Team member deleted successfully!');
        loadTeamMembers();
        // Reload team members in tasks.js for filters
        if (document.getElementById('filterAssignee')) {
            const assigneeFilter = document.getElementById('filterAssignee');
            assigneeFilter.innerHTML = '<option value="all">All</option>';
            const team = await API.getTeam();
            team.members.forEach(m => {
                const option = document.createElement('option');
                option.value = m.name;
                option.textContent = m.name;
                assigneeFilter.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Failed to delete member:', error);
        alert('Error: ' + error.message);
    }
}

// Escape HTML helper
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

