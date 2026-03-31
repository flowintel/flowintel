*move to user manual in a later stage*

# Setting up a demo environment

Flowintel ships with sample cases and a community data set. A development installation imports the sample cases automatically during setup, so users have something to explore straight away. A production installation starts with a clean database and skips this data entirely.

If you are setting up a production instance for demo or training purposes, you can import the test data manually. This page describes the available data sets, how to import them, and how to clean up afterwards.

There are two approaches, depending on what you need:

| Approach | Use case | Method | What it creates |
|----------|----------|--------|-----------------|
| **Sample cases only** | Quick testing or exploration | Imports directly into the database; Flowintel does not need to be running | Two pre-built cases under the admin user |
| **Full community data set** | Demos and training | Uses the REST API; requires an admin API key and Flowintel to be running | Step 1: organisations, users and roles. Step 2: cases assigned across organisations with the privileged workflow active |


## What is included

The test data has two layers that build on each other:

1. **Sample cases**: two pre-built cases stored as JSON files in `tests/testdata/`.
2. **Community data**: organisations, users, roles and case assignments that simulate a multi-team environment. This layer is imported manually and is designed for demo sites where you want to show how Flowintel handles collaboration between different organisations.

### Sample cases

The `tests/testdata/` directory contains two case files:

| File | Case title | Description |
|------|-----------|-------------|
| `case_ForensicCase.json` | Forensic Case | A forensic investigation with four tasks covering disk extraction, timeline creation, evtx analysis, and report writing |
| `case_NewCompromisedWorkstation.json` | New Compromised Workstation | A malware investigation scenario with multiple tasks, subtasks, URL tools, deadlines, and MISP objects |

Each file is a JSON document with the case metadata, tasks, notes, subtasks, tags, URL tools and (where applicable) MISP objects. The import creates all of these records at once.

### Community data

The community data set is defined in `tests/testdata/test-data-community.json`. It creates two organisations with a total of eight users spread across four custom roles:

| Organisation | Users | Roles represented |
|---|---|---|
| LEA Organisation | Alice Manager, Bob Officer, Carol Officer, Dave Deputy, Eve Comms | OrgAdmin, CaseAdmin, QueueAdmin, Queuer, Read Only |
| CSIRT Organisation | Frank TeamLead, Grace Handler, Hank Junior | OrgAdmin, CaseAdmin, Queuer |

When you import this data, all users share the same randomly generated passphrase (for example `BrightCastle42`). Each user also receives a unique API key. The script prints the shared password to the terminal and saves the API keys to a local file so the case import script can authenticate as individual community users.

After importing the community users, you can import the sample cases through the REST API. This second step assigns cases to organisations, creates tasks as different users, sets cases as privileged and distributes task assignments randomly. The result is a realistic multi-organisation workspace with notifications and approval queues.


## Importing sample cases only

If you only need the two sample cases and do not need community organisations or users, you can import them in one step.

Make sure Flowintel is **not** running (or run this in a separate terminal before starting it):

```bash
cd /opt/flowintel/flowintel
source env/bin/activate
python3 app.py -td
```

The `-td` flag tells Flowintel to load every `case_*.json` file from `tests/testdata/` and import it under the admin user. You see a confirmation for each case:

```
  Created: Forensic Case
  Created: New Compromised Workstation
```

This approach creates the cases directly in the database. It does not require the REST API to be running.


## Importing the full community data set

The full community import is a two-step process. Both steps use the REST API, so Flowintel must be running.

### Step 1: Create organisations, roles and users

You need an admin API key for this step. You can find it in the Flowintel web interface under your profile, or retrieve it from the database.

Run the import through `launch.sh` (the `-tdc` flag stands for "test data community"):

```bash
bash launch.sh -tdc <your-admin-api-key>
```

Or call the script directly:

```bash
source env/bin/activate
python3 tests/testdata/init_community_data.py create --api-key <your-admin-api-key>
```

If Flowintel is running on a non-default address or port, add the `--url` flag:

```bash
python3 tests/testdata/init_community_data.py create --api-key <your-admin-api-key> --url http://192.168.1.50:7006
```

The script:

1. Reads the organisation and user definitions from `tests/testdata/test-data-community.json`
2. Creates each organisation through the admin API
3. Creates the necessary roles
4. Creates each user with the correct role and organisation membership
5. Generates a single random passphrase shared by all community users and prints it to the terminal
6. Saves all user API keys to `tests/testdata/.community-api-keys.json`

Take note of the shared password. Every community user is created with this same password, so you need it to log in as different users.

A successful run looks like this:

```
$ bash launch.sh -tdc <your-admin-api-key>
Creating roles...
  Created: OrgAdmin
  Created: CaseAdmin
  Created: QueueAdmin
  Created: Queuer
Creating organisations...
  Created: LEA Organisation
  Created: CSIRT Organisation
Creating users...
  Created: Alice Manager (OrgAdmin)
  Created: Bob Officer (CaseAdmin)
  Created: Carol Officer (QueueAdmin)
  Created: Dave Deputy (Queuer)
  Created: Eve Comms (Read Only)
  Created: Frank TeamLead (OrgAdmin)
  Created: Grace Handler (CaseAdmin)
  Created: Hank Junior (Queuer)

API keys saved to /opt/flowintel/flowintel/tests/testdata/.community-api-keys.json

Shared password for all community users: CalmMeadow77

--- Community test data overview ---

Organisation: LEA Organisation
  User                      Email                                    Role
  ------------------------- ---------------------------------------- ---------------
  Alice Manager             alice.manager@lea-org.local              OrgAdmin
  Bob Officer               bob.officer@lea-org.local                CaseAdmin
  Carol Officer             carol.officer@lea-org.local              QueueAdmin
  Dave Deputy               dave.deputy@lea-org.local                Queuer
  Eve Comms                 eve.comms@lea-org.local                  Read Only

Organisation: CSIRT Organisation
  User                      Email                                    Role
  ------------------------- ---------------------------------------- ---------------
  Frank TeamLead            frank.teamlead@csirt-org.local           OrgAdmin
  Grace Handler             grace.handler@csirt-org.local            CaseAdmin
  Hank Junior               hank.junior@csirt-org.local              Queuer
```

### Step 2: Create community cases

Once the organisations, roles and users exist, import the sample cases through the REST API. This step does not require an admin API key because it reads the per-user keys from `.community-api-keys.json`, saved in the previous step.

Run the import through `launch.sh` (the `-tdcc` flag stands for "test data community cases"):

```bash
bash launch.sh -tdcc
```

Or call the script directly:

```bash
source env/bin/activate
python3 tests/testdata/init_community_cases.py create
```

Again, add `--url` if Flowintel is running on a non-default address:

```bash
python3 tests/testdata/init_community_cases.py create --url http://192.168.1.50:7006
```

The script:

1. Loads the API keys from `.community-api-keys.json`
2. For each case file in `tests/testdata/`, creates the case as a CaseAdmin user from a randomly selected organisation
3. Sets each case as privileged, which triggers the approval workflow
4. Creates tasks as a Queuer user, which generates task-requested notifications for approvers
5. Adds notes, subtasks and URL tools to each task
6. Randomly assigns tasks to users across organisations
7. Creates MISP objects if the case file includes them

Each case title is prefixed with a random identifier (for example `TC-ABC47`) so you can run the import multiple times without name collisions. Every case description is also tagged with `[community-test-case]` so the cleanup script can find and remove them later.

A successful run looks like this:

```
$ bash launch.sh -tdcc
Importing test cases...
  Created case: TC-4JUP8 Forensic Case (org: CSIRT Organisation)
    Task: Extract disk
    Task: Create a timeline
    Task: Extract and analyze evtx
    Task: Write report
  Created case: TC-401S9 New Compromised Workstation (org: LEA Organisation)
    Task: Immediate containment
    Task: Evidence collection
    Task: Malware analysis
    Task: Scope and impact assessment
    Task: Eradication and recovery
    Task: Update MISP / threat repository
    Task: Post-incident review

--- Community test cases overview ---
  Case title                                    Organisation              Tasks
  --------------------------------------------- ------------------------- ------
  TC-4JUP8 Forensic Case                        CSIRT Organisation        4
  TC-401S9 New Compromised Workstation          LEA Organisation          7
```


## Removing test data

There are three ways to remove imported data, depending on how much you want to clean up.

### Remove community cases only

This deletes all cases whose description contains the `[community-test-case]` tag. It does not remove the community users, roles or organisations.

```bash
bash launch.sh -dtdcc
```

Or directly:

```bash
source env/bin/activate
python3 tests/testdata/init_community_cases.py delete
```

### Remove community users, roles and organisations

This removes the users, roles and organisations created by the community data script. You need the admin API key again:

```bash
bash launch.sh -dtdc <your-admin-api-key>
```

Or directly:

```bash
source env/bin/activate
python3 tests/testdata/init_community_data.py delete --api-key <your-admin-api-key>
```

The script also deletes the `.community-api-keys.json` file.

When removing the full community data set, delete the cases first (with `-dtdcc`), then the users, roles and organisations (with `-dtdc`).

### Remove all cases and templates

To wipe all case data from the database (not just community test data), use the database cleaner script:

```bash
source env/bin/activate
python3 bin/clean_database.py
```

The script shows a summary of what will be deleted and asks for confirmation. To skip the prompt (for example in a scripted setup), pass the `--force` flag:

```bash
python3 bin/clean_database.py --force
```

This removes all cases, tasks, notes, subtasks, templates, notifications and file records. It does not remove user accounts, organisations, roles, taxonomies or MISP module data.


## Quick-reference table

| Action | `launch.sh` flag | Direct command |
|--------|-------------------|----------------|
| Import sample cases (database) | Built into `-i` (dev init) | `python3 app.py -td` |
| Create community users, roles and organisations | `-tdc <api-key>` | `python3 tests/testdata/init_community_data.py create --api-key <key>` |
| Create community cases | `-tdcc` | `python3 tests/testdata/init_community_cases.py create` |
| Delete community cases | `-dtdcc` | `python3 tests/testdata/init_community_cases.py delete` |
| Delete community users, roles and organisations | `-dtdc <api-key>` | `python3 tests/testdata/init_community_data.py delete --api-key <key>` |
| Wipe all cases and templates | — | `python3 bin/clean_database.py` |
