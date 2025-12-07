// Task Management
let allTasks = [];
let teamMembers = [];

// Load team members
async function loadTeamMembers() {
    try {
        const team = await API.getTeam();
        teamMembers = team.members;
        
        // Populate assignee filter
        const assigneeFilter = document.getElementById('filterAssignee');
        teamMembers.forEach(member => {
            const option = document.createElement('option');
            option.value = member.name;
            option.textContent = member.name;
            assigneeFilter.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load team:', error);
    }
}

// Display tasks
function displayTasks(tasks) {
    allTasks = tasks;
    applyFilters();
    updateSummary(tasks);
}

// Apply filters
function applyFilters() {
    const priorityFilter = document.getElementById('filterPriority').value;
    const assigneeFilter = document.getElementById('filterAssignee').value;
    const statusFilter = document.getElementById('filterStatus').value;

    let filtered = allTasks.filter(task => {
        // Priority filter
        if (priorityFilter !== 'all' && task.priority !== priorityFilter) {
            return false;
        }

        // Assignee filter
        if (assigneeFilter !== 'all' && task.assigned_to !== assigneeFilter) {
            return false;
        }

        // Status filter
        if (statusFilter === 'assigned' && !task.assigned_to) {
            return false;
        }
        if (statusFilter === 'unassigned' && task.assigned_to) {
            return false;
        }

        return true;
    });

    renderTasks(filtered);
}

// Render tasks
function renderTasks(tasks) {
    const tasksGrid = document.getElementById('tasksGrid');
    tasksGrid.innerHTML = '';

    if (tasks.length === 0) {
        tasksGrid.innerHTML = '<p style="text-align: center; color: var(--text-secondary); grid-column: 1 / -1;">No tasks found matching the filters.</p>';
        return;
    }

    tasks.forEach(task => {
        const taskCard = createTaskCard(task);
        tasksGrid.appendChild(taskCard);
    });
}

// Create task card
function createTaskCard(task) {
    const card = document.createElement('div');
    card.className = `task-card priority-${task.priority || 'medium'}`;
    card.onclick = () => showTaskModal(task);

    const deadline = task.deadline ? new Date(task.deadline).toLocaleDateString() : null;
    const deadlineTime = task.deadline ? new Date(task.deadline).toLocaleTimeString() : null;

    card.innerHTML = `
        <div class="task-header">
            <span class="task-id">Task #${task.id}</span>
            ${task.priority ? `<span class="task-priority ${task.priority}">${task.priority}</span>` : ''}
        </div>
        <div class="task-description">${escapeHtml(task.description)}</div>
        <div class="task-meta">
            ${task.assigned_to ? `
                <div class="task-meta-item">
                    <strong>Assigned to:</strong> ${escapeHtml(task.assigned_to)}
                </div>
            ` : ''}
            ${deadline ? `
                <div class="task-meta-item">
                    <strong>Deadline:</strong> ${deadline} ${deadlineTime}
                </div>
            ` : ''}
            ${task.assignment_confidence ? `
                <div class="task-meta-item">
                    <strong>Confidence:</strong> ${Math.round(task.assignment_confidence * 100)}%
                </div>
            ` : ''}
        </div>
        ${task.assigned_to ? `
            <div class="task-assignee">
                <span>👤</span>
                <span>${escapeHtml(task.assigned_to)}</span>
            </div>
        ` : `
            <div class="task-assignee unassigned">
                <span>⚠️</span>
                <span>Unassigned</span>
            </div>
        `}
        ${task.required_skills && task.required_skills.length > 0 ? `
            <div class="task-tags">
                ${task.required_skills.map(skill => `<span class="task-tag">${escapeHtml(skill)}</span>`).join('')}
            </div>
        ` : ''}
    `;

    return card;
}

// Update summary
function updateSummary(tasks) {
    document.getElementById('totalTasks').textContent = tasks.length;
    document.getElementById('assignedTasks').textContent = tasks.filter(t => t.assigned_to).length;
    document.getElementById('tasksWithDeadline').textContent = tasks.filter(t => t.deadline).length;
    document.getElementById('criticalTasks').textContent = tasks.filter(t => t.priority === 'critical').length;
}

// Clear filters
function clearFilters() {
    document.getElementById('filterPriority').value = 'all';
    document.getElementById('filterAssignee').value = 'all';
    document.getElementById('filterStatus').value = 'all';
    applyFilters();
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize filters
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('filterPriority').addEventListener('change', applyFilters);
    document.getElementById('filterAssignee').addEventListener('change', applyFilters);
    document.getElementById('filterStatus').addEventListener('change', applyFilters);
    loadTeamMembers();
});

