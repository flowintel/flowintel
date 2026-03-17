#!/usr/bin/env python3
"""
Clean the Flowintel database by removing:
- All cases (and their related data)
- All tasks
- All notes
- All case, task, and note templates
"""

import sys
import os

# Add the app to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.db_class.db import (
    Case, Task, Note, Subtask,
    Case_Template, Task_Template, Note_Template, Subtask_Template,
    Note_Template_Model, Case_Note_Template_Model,
    Case_Task_Template,
    Case_Template_Tags, Task_Template_Tags,
    Case_Template_Galaxy_Tags, Task_Template_Galaxy_Tags,
    Case_Template_Custom_Tags, Task_Template_Custom_Tags,
    Case_Template_Connector_Instance,
    Task_Template_Url_Tool,
    Task_User, Case_Org,
    Notification,
    File
)


def count_records():
    """Count records that will be deleted."""
    counts = {
        'Cases': Case.query.count(),
        'Tasks': Task.query.count(),
        'Notes': Note.query.count(),
        'Subtasks': Subtask.query.count(),
        'Case Templates': Case_Template.query.count(),
        'Task Templates': Task_Template.query.count(),
        'Note Templates': Note_Template.query.count(),
        'Subtask Templates': Subtask_Template.query.count(),
        'Note Template Models': Note_Template_Model.query.count(),
    }
    return counts


def clean_database():
    """Remove all cases, tasks, notes, and templates from the database."""
    
    print("\n" + "="*60)
    print("FLOWINTEL DATABASE CLEANER")
    print("="*60)
    
    # Count records before deletion
    counts = count_records()
    
    print("\nRecords to be deleted:")
    print("-"*40)
    total = 0
    for name, count in counts.items():
        print(f"  {name}: {count}")
        total += count
    print("-"*40)
    print(f"  TOTAL: {total} records")
    
    if total == 0:
        print("\nDatabase is already clean. Nothing to delete.")
        return
    
    print("\nDeleting records...")
    
    try:        
        # 1. Delete case-related junction tables and related data
        print("  - Removing case organisations...")
        Case_Org.query.delete()
        
        print("  - Removing task assignments...")
        Task_User.query.delete()
        
        print("  - Removing notifications...")
        Notification.query.delete()
        
        print("  - Removing files...")
        File.query.delete()
        
        # 2. Delete notes (before tasks, as notes belong to tasks)
        print("  - Removing notes...")
        Note.query.delete()
        
        # 3. Delete subtasks (before tasks)
        print("  - Removing subtasks...")
        Subtask.query.delete()
        
        # 4. Delete tasks (before cases, as tasks belong to cases)
        print("  - Removing tasks...")
        Task.query.delete()
        
        # 5. Delete cases
        print("  - Removing cases...")
        Case.query.delete()
        
        # 6. Delete template-related junction tables
        print("  - Removing template tags...")
        Case_Template_Tags.query.delete()
        Task_Template_Tags.query.delete()
        Case_Template_Galaxy_Tags.query.delete()
        Task_Template_Galaxy_Tags.query.delete()
        Case_Template_Custom_Tags.query.delete()
        Task_Template_Custom_Tags.query.delete()
        
        print("  - Removing template connector instances...")
        Case_Template_Connector_Instance.query.delete()
        
        print("  - Removing template URL tools...")
        Task_Template_Url_Tool.query.delete()
        
        print("  - Removing case-task template associations...")
        Case_Task_Template.query.delete()
        
        print("  - Removing case-note template associations...")
        Case_Note_Template_Model.query.delete()
        
        # 7. Delete note templates
        print("  - Removing note templates...")
        Note_Template.query.delete()
        
        # 8. Delete note template models
        print("  - Removing note template models...")
        Note_Template_Model.query.delete()
        
        # 9. Delete subtask templates
        print("  - Removing subtask templates...")
        Subtask_Template.query.delete()
        
        # 10. Delete task templates
        print("  - Removing task templates...")
        Task_Template.query.delete()
        
        # 11. Delete case templates
        print("  - Removing case templates...")
        Case_Template.query.delete()
        
        # Commit all changes
        db.session.commit()
        
        print("\n" + "="*60)
        print("SUCCESS! Database cleaned.")
        print("="*60)
        
        # Show counts after deletion
        counts_after = count_records()
        print("\nRecords remaining:")
        for name, count in counts_after.items():
            print(f"  {name}: {count}")
        
    except Exception as e:
        db.session.rollback()
        print(f"\nERROR: Failed to clean database: {e}")
        raise


def main():
    force = '--force' in sys.argv or '-f' in sys.argv
    
    app = create_app()
    
    with app.app_context():
        if not force:
            print("\n" + "!"*60)
            print("WARNING: This will permanently delete ALL data!")
            print("!"*60)
            
            counts = count_records()
            total = sum(counts.values())
            
            if total > 0:
                response = input(f"\nAre you sure you want to delete {total} records? (yes/no): ")
                if response.lower() != 'yes':
                    print("Aborted.")
                    return
        
        clean_database()


if __name__ == '__main__':
    main()
