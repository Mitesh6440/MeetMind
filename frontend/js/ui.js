// UI Updates and Display Functions

// Reset UI to initial state
function resetUIState() {
    // Hide all sections
    const uploadSection = document.getElementById('uploadSection');
    const resultsSection = document.getElementById('resultsSection');
    const teamSection = document.getElementById('teamSection');
    
    if (uploadSection) uploadSection.style.display = 'none';
    if (resultsSection) resultsSection.style.display = 'none';
    if (teamSection) teamSection.style.display = 'none';
    
    // Show upload section by default
    if (uploadSection) uploadSection.style.display = 'block';
    
    // Reset progress if function exists
    if (typeof resetProgress === 'function') {
        resetProgress();
    } else if (window.resetProgress && typeof window.resetProgress === 'function') {
        window.resetProgress();
    }
}

// Display results after processing
function displayResults(result) {
    // Hide upload section and team section, show results
    const uploadSection = document.getElementById('uploadSection');
    const teamSection = document.getElementById('teamSection');
    const resultsSection = document.getElementById('resultsSection');
    
    if (uploadSection) uploadSection.style.display = 'none';
    if (teamSection) teamSection.style.display = 'none';
    if (resultsSection) resultsSection.style.display = 'block';
    
    // Show back button in header
    const backToUploadBtn = document.getElementById('backToUploadBtn');
    if (backToUploadBtn) {
        backToUploadBtn.style.display = 'inline-block';
    }

    // Display tasks
    if (result.tasks && result.tasks.length > 0) {
        displayTasks(result.tasks);
    } else {
        // If no tasks, show message
        const tasksGrid = document.getElementById('tasksGrid');
        if (tasksGrid) {
            tasksGrid.innerHTML = '<p style="text-align: center; color: var(--text-secondary); grid-column: 1 / -1; padding: 2rem;">No tasks were extracted from the audio.</p>';
        }
    }

    // Display dependency graph
    if (result.dependency_graph && result.dependency_graph.edges.length > 0) {
        displayDependencyGraph(result.dependency_graph);
    }

    // Display transcript
    if (result.transcript_text) {
        displayTranscript(result.transcript_text);
    }
}

// Display transcript
function displayTranscript(transcript) {
    const transcriptSection = document.getElementById('transcriptSection');
    const transcriptContent = document.getElementById('transcriptContent');
    
    transcriptSection.style.display = 'block';
    transcriptContent.textContent = transcript;
}

// Show task modal
function showTaskModal(task) {
    const modal = document.getElementById('taskModal');
    const modalTitle = document.getElementById('modalTaskTitle');
    const modalContent = document.getElementById('modalTaskContent');

    modalTitle.textContent = `Task #${task.id}`;

    const deadline = task.deadline ? new Date(task.deadline).toLocaleString() : 'Not set';
    const priority = task.priority || 'Not set';
    const assignedTo = task.assigned_to || 'Unassigned';
    const confidence = task.assignment_confidence ? Math.round(task.assignment_confidence * 100) + '%' : 'N/A';
    const reasoning = task.assignment_reasoning || 'No reasoning provided';

    modalContent.innerHTML = `
        <div style="margin-bottom: 1.5rem;">
            <h3 style="margin-bottom: 0.5rem;">Description</h3>
            <p style="color: var(--text-secondary);">${escapeHtml(task.description)}</p>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
            <div>
                <strong>Priority:</strong>
                <span class="task-priority ${priority}">${priority}</span>
            </div>
            <div>
                <strong>Deadline:</strong>
                <p style="color: var(--text-secondary); margin-top: 0.25rem;">${deadline}</p>
            </div>
            <div>
                <strong>Assigned To:</strong>
                <p style="color: var(--text-secondary); margin-top: 0.25rem;">${escapeHtml(assignedTo)}</p>
            </div>
            <div>
                <strong>Confidence:</strong>
                <p style="color: var(--text-secondary); margin-top: 0.25rem;">${confidence}</p>
            </div>
        </div>

        ${task.required_skills && task.required_skills.length > 0 ? `
            <div style="margin-bottom: 1.5rem;">
                <strong>Required Skills:</strong>
                <div class="task-tags" style="margin-top: 0.5rem;">
                    ${task.required_skills.map(skill => `<span class="task-tag">${escapeHtml(skill)}</span>`).join('')}
                </div>
            </div>
        ` : ''}

        ${task.technical_terms && task.technical_terms.length > 0 ? `
            <div style="margin-bottom: 1.5rem;">
                <strong>Technical Terms:</strong>
                <div style="margin-top: 0.5rem;">
                    ${task.technical_terms.map(term => `<span class="task-tag">${escapeHtml(term)}</span>`).join('')}
                </div>
            </div>
        ` : ''}

        ${task.dependencies && task.dependencies.length > 0 ? `
            <div style="margin-bottom: 1.5rem;">
                <strong>Dependencies:</strong>
                <p style="color: var(--text-secondary); margin-top: 0.25rem;">
                    Depends on tasks: ${task.dependencies.join(', ')}
                </p>
            </div>
        ` : ''}

        <div>
            <strong>Assignment Reasoning:</strong>
            <p style="color: var(--text-secondary); margin-top: 0.25rem; line-height: 1.6;">${escapeHtml(reasoning)}</p>
        </div>
    `;

    modal.style.display = 'block';
}

// Close task modal
function closeTaskModal() {
    document.getElementById('taskModal').style.display = 'none';
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('taskModal');
    if (event.target === modal) {
        closeTaskModal();
    }
}

// Go back to upload section
function goBackToUpload() {
    // Hide results section
    const resultsSection = document.getElementById('resultsSection');
    if (resultsSection) {
        resultsSection.style.display = 'none';
    }
    
    // Hide team section
    const teamSection = document.getElementById('teamSection');
    if (teamSection) {
        teamSection.style.display = 'none';
    }
    
    // Show upload section
    const uploadSection = document.getElementById('uploadSection');
    if (uploadSection) {
        uploadSection.style.display = 'block';
    }
    
    // Hide back button in header
    const backToUploadBtn = document.getElementById('backToUploadBtn');
    if (backToUploadBtn) {
        backToUploadBtn.style.display = 'none';
    }
    
    // Reset progress and file input
    if (window.resetProgress && typeof window.resetProgress === 'function') {
        window.resetProgress();
    }
    
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Escape HTML helper
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

