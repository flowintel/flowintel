// Helper functions for case and task operations in privileged cases

function isApprover(casesInfo) {
    return casesInfo.permission.admin || casesInfo.permission.case_admin || casesInfo.permission.queue_admin;
}

// Whether the current user can edit a task that is in a restricted status
// (Requested, Rejected or Request Review) in a privileged case.
export function canEditRestrictedTask(task, casesInfo, statusInfo) {
    if (!statusInfo || !casesInfo.case) return true;
    
    const isRestricted = casesInfo.case.privileged_case && 
                         (task.status_id === statusInfo.config.TASK_REQUESTED || 
                          task.status_id === statusInfo.config.TASK_REJECTED ||
                          task.status_id === statusInfo.config.TASK_REQUEST_REVIEW);
    
    if (!isRestricted) return true;
    
    return isApprover(casesInfo);
}

// Whether the current user can modify a privileged case (Admin or Case Admin only).
export function canModifyPrivilegedCase(casesInfo) {
    if (!casesInfo?.case?.privileged_case) return true;
    return casesInfo.permission.admin || casesInfo.permission.case_admin;
}

// Returns the list of statuses a task can transition to, based on
// case privileges and the user's role.
//
// In a privileged case:
//  - Requested tasks: only approvers can change, limited to Approved/Rejected
//  - Request Review tasks: approvers see all except Requested (disabled)
//  - Other tasks: queuers see only Created, Ongoing, Request Review
export function getAvailableStatuses(task, casesInfo, statusInfo) {
    if (!statusInfo) return [];
    
    const isPrivileged = casesInfo?.case?.privileged_case;
    
    // Requested: only allow approval or rejection
    if (isPrivileged && task.status_id === statusInfo.config.TASK_REQUESTED) {
        const allowedStatusIds = [
            statusInfo.config.TASK_REQUESTED,
            statusInfo.config.TASK_APPROVED,
            statusInfo.config.TASK_REJECTED
        ];
        return statusInfo.status.filter(status => {
            if (status.id === task.status_id) return false;
            return allowedStatusIds.includes(status.id);
        });
    }
    
    // Request Review: show all but disable Requested (not a valid transition)
    if (isPrivileged && task.status_id === statusInfo.config.TASK_REQUEST_REVIEW) {
        return statusInfo.status
            .filter(status => status.id !== task.status_id)
            .map(status => ({
                ...status,
                disabled: status.id === statusInfo.config.TASK_REQUESTED
            }));
    }
    
    // Queuers in a privileged case: limited transitions
    if (isPrivileged && !isApprover(casesInfo)) {
        return statusInfo.status.filter(status => {
            if (status.id === task.status_id) return false;
            return status.id === statusInfo.config.TASK_REQUEST_REVIEW || status.name === 'Created' || status.name === 'Ongoing';
        });
    }
    
    // Default: all statuses except current
    return statusInfo.status.filter(status => status.id !== task.status_id);
}

// Whether the status dropdown should be disabled (non-approver on a restricted task).
export function isStatusDropdownDisabled(task, casesInfo, statusInfo) {
    if (!statusInfo || !casesInfo.case) return false;
    if (!casesInfo.case.privileged_case) return false;
    
    const isRestricted = task.status_id === statusInfo.config.TASK_REQUESTED || 
                         task.status_id === statusInfo.config.TASK_REQUEST_REVIEW;
    
    return isRestricted && !isApprover(casesInfo);
}

// In a privileged case, whether the task complete button should be disabled
// (task must be in "Finished" status before it can be completed).
export function isCompleteTaskDisabled(task, casesInfo, statusInfo) {
    if (!statusInfo || !casesInfo?.case?.privileged_case) return false;
    if (task.completed) return false;  // revive is always allowed
    const finishedStatus = statusInfo.status.find(s => s.name === 'Finished');
    return finishedStatus && task.status_id !== finishedStatus.id;
}

// Tooltip explaining why the complete button is disabled.
export function getCompleteTaskTooltip(task, casesInfo, statusInfo) {
    if (isCompleteTaskDisabled(task, casesInfo, statusInfo)) {
        return 'Set the task status to Finished before completing it';
    }
    return task.completed ? 'Revive the task' : 'Complete the task';
}

// Tooltip explaining why the dropdown is disabled.
export function getStatusDropdownTooltip(task, casesInfo, statusInfo) {
    if (isStatusDropdownDisabled(task, casesInfo, statusInfo)) {
        if (task.status_id === statusInfo.config.TASK_REQUEST_REVIEW) {
            return 'Task in Request Review status in a privileged case can only be modified by Admin, Case Admin or Queue Admin';
        }
        return 'Task in Requested status in a privileged case can only be modified by Admin, Case Admin or Queue Admin';
    }
    return '';
}
