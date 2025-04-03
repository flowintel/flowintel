<img title="" src="./doc/flowintel_logo.png" alt="" width="149" data-align="center">

Flowintel is an open-source platform designed to assist analysts in organizing their cases and tasks. It features a range of tools and functionalities to enhance workflow efficiency. 

## Features

- **Case and Task Management**: Tailored for security analysts, enabling efficient tracking and organization.

- **Rich Documentation Tools**: Includes Markdown and Mermaid integration for detailed notes, with export options like PDF.

- **Integration with MISP standard**: Seamless connection with [MISP taxonomies](https://github.com/MISP/misp-taxonomies) and [MISP galaxy](https://www.misp-galaxy.org/).

- **Calendar and Notifications**: Features an efficient calendar view and notifications for timely task management.

- **Templating System**: Provides templates for cases and tasks, creating a playbook and process repository for cybersecurity.

- **Flexible Data Export**: Offers modules for exporting data to platforms like [MISP](https://www.misp-project.org/), [AIL](https://www.ail-project.org/), and more.

- **Accessible API**: Exposes an API for easy interaction with FlowIntel's functionalities.

- **Advanced Analysis Modules**: Leverages MISP modules for automated enrichment, threat intelligence, and data correlation.

- **User and Workflow Management**: Supports organizational structuring, task assignments, and a queueing system for efficient workload distribution.

- **Comprehensive Audit Logging**: Maintains a full audit trail of all actions, ensuring transparency and compliance.

![task-management](./doc/case_example.png)


## Quick start

Change the **configuration** `/conf/config.py`

run the **installation** script `./install.sh`

**Start** the application with `./launch.sh -l`

#### Account

- email: `admin@admin.admin`

- password: `admin`

## Documentation
A more detailed documentation can be found here: [flowintel.github.io/flowintel-doc](flowintel.github.io/flowintel-doc)

## License

This software is licensed under [GNU Affero General Public License version 3](http://www.gnu.org/licenses/agpl-3.0.html)

```
Copyright (C) 2022-2023 CIRCL - Computer Incident Response Center Luxembourg
Copyright (C) 2022-2023 David Cruciani
```

## Funding

![CIRCL.lu](https://www.circl.lu/assets/images/logo.png)
![CEF Telecom funding (D4 Project](https://www.misp-project.org/assets/images/en_cef.png)
