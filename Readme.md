
# Employee Appraisal Management System (EAMS)

## Overview
The Employee Appraisal Management System (EAMS) is a web-based application designed to streamline and automate the employee performance evaluation process. This system facilitates efficient management of employee appraisals, goal setting, and performance tracking.

## Tech Stack
- **Frontend**: 
  - HTML (62%)
  - CSS (16.3%)
  - JavaScript (3.7%)
- **Backend**: 
  - Python (18%)

## Features
1. **Employee Management**
   - Employee profile management
   - Department and role management
   - Employee history tracking

2. **Appraisal Process**
   - Goal setting and tracking
   - Performance evaluation forms
   - Self-assessment capabilities
   - Manager assessment interface
   - Rating system implementation

3. **Goals Management**
   - Create and assign goals
   - Track goal progress
   - Link goals to company objectives
   - Performance metrics tracking

4. **Reporting and Analytics**
   - Performance reports generation
   - Analytics dashboard
   - Historical data comparison
   - Export capabilities

## Installation

### Prerequisites
- Python 3.x
- Web server (e.g., Apache, Nginx)
- Database system

### Setup Steps
1. Clone the repository
   ```bash
   git clone https://github.com/rahul-ofis/EAMS.git
   cd EAMS
   ```

2. Create a virtual environment
   ```bash
   python -m venv venv
   source venv/bin/activate  # For Unix/Linux
   # or
   venv\Scripts\activate     # For Windows
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Configure the application
   - Set up your database configurations
   - Configure environment variables
   - Set up email settings (if applicable)

5. Run the application
   ```bash
   python manage.py runserver
   ```

## Directory Structure
```
EAMS/
├── static/          # CSS, JavaScript, and static files
├── templates/       # HTML templates
├── app/            # Main application code
├── config/         # Configuration files
└── docs/           # Documentation
```

## Usage
1. Access the system through your web browser
2. Login with your credentials
3. Navigate through different modules:
   - Employee Management
   - Goal Setting
   - Appraisal Forms
   - Reports Generation

## Security Features
- Secure authentication system
- Role-based access control
- Data encryption
- Session management

## Contributing
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Support
For support and queries, please contact:
- Create an issue in the repository
- Contact the maintainers

## License
© 2024 AlphaNimble. All rights reserved.

## Authors and Acknowledgment
- Maintained by: rahul-ofis

## Project Status
Under active development - Version 2.0

---
Last Updated: 2025-01-03