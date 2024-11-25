# Django Interview Pipeline

A Django-based interview management system that processes and analyzes interview responses using natural language processing techniques.

## Features

- Structured interview pipeline with multiple stages
- Advanced response processing and data extraction
- Support for concurrent interview sessions
- Detailed analysis of:
  - Experience and company history
  - Technical and soft skills categorization
  - Role responsibilities and achievements
  - Project details and outcomes
  - Problem-solving approaches

## Setup

1. Clone the repository:
```bash
git clone [your-repo-url]
cd Django_v1
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run migrations:
```bash
python manage.py migrate
```

5. Run the development server:
```bash
python manage.py runserver
```

## Testing

Run the test suite:
```bash
python manage.py test
```

## License

MIT License
