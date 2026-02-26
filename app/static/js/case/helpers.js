/**
 * Helper functions for case and task operations
 */

/**
 * Check if current user can edit a task in a restricted state (Requested or Rejected status in privileged case)
 * @param {Object} task - The task object
 * @param {Object} casesInfo - The cases_info object containing case and permission details
 * @param {Object} statusInfo - The status_info object containing status configuration
 * @returns {boolean} - True if user can edit the restricted task
 */
export function canEditRestrictedTask(task, casesInfo, statusInfo) {
    if (!statusInfo || !casesInfo.case) return true;
    
    const isRestricted = casesInfo.case.privileged_case && 
                         (task.status_id === statusInfo.config.TASK_REQUESTED || 
                          task.status_id === statusInfo.config.TASK_REJECTED);
    
    if (!isRestricted) return true;
    
    return casesInfo.permission.admin || 
           casesInfo.permission.case_admin || 
           casesInfo.permission.queue_admin;
}

/**
 * Check if current user can modify a privileged case
 * @param {Object} casesInfo - The cases_info object containing case and permission details
 * @returns {boolean} - True if user can modify the privileged case
 */
export function canModifyPrivilegedCase(casesInfo) {
    if (!casesInfo?.case?.privileged_case) return true;
    return casesInfo.permission.admin || casesInfo.permission.case_admin;
}

/**
 * Get available statuses for a task based on its current status and case privileges
 * @param {Object} task - The task object
 * @param {Object} casesInfo - The cases_info object
 * @param {Object} statusInfo - The status_info object
 * @returns {Array} - Array of available status objects
 */
export function getAvailableStatuses(task, casesInfo, statusInfo) {
    if (!statusInfo) return [];
    
    const isRequestedPrivileged = casesInfo?.case?.privileged_case && 
                                 task.status_id === statusInfo.config.TASK_REQUESTED;
    
    return statusInfo.status.filter(status => {
        if (status.id === task.status_id) return false;
        
        if (isRequestedPrivileged) {
            const allowedStatusIds = [
                statusInfo.config.TASK_REQUESTED,
                statusInfo.config.TASK_APPROVED,
                statusInfo.config.TASK_REJECTED
            ];
            return allowedStatusIds.includes(status.id);
        }
        
        return true;
    });
}

/**
 * Check if status dropdown should be disabled for a task
 * @param {Object} task - The task object
 * @param {Object} casesInfo - The cases_info object
 * @param {Object} statusInfo - The status_info object
 * @returns {boolean} - True if dropdown should be disabled
 */
export function isStatusDropdownDisabled(task, casesInfo, statusInfo) {
    if (!statusInfo || !casesInfo.case) return false;
    
    return casesInfo.case.privileged_case && 
           task.status_id === statusInfo.config.TASK_REQUESTED && 
           !casesInfo.permission.admin && 
           !casesInfo.permission.case_admin && 
           !casesInfo.permission.queue_admin;
}

/**
 * Get tooltip message for status dropdown
 * @param {Object} task - The task object
 * @param {Object} casesInfo - The cases_info object
 * @param {Object} statusInfo - The status_info object
 * @returns {string} - Tooltip message or empty string
 */
export function getStatusDropdownTooltip(task, casesInfo, statusInfo) {
    if (isStatusDropdownDisabled(task, casesInfo, statusInfo)) {
        return 'Task in Requested status in a privileged case can only be modified by Admin, Case Admin or Queue Admin';
    }
    return '';
}
