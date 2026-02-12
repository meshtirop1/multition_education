# MultiTion Education Platform

A professional, full-stack AI education platform built with Django, featuring student-mentor communication, community forums, role-based dashboards, and automated certificates.

## Quick Start
```bash
pip install -r requirements.txt
python manage.py runserver
```
Visit http://localhost:8000

## Demo Accounts
| Role | Username | Password |
|------|----------|----------|
| Admin | admin | admin123 |
| Mentor | dr_sarah | mentor123 |
| Mentor | prof_james | mentor123 |
| Student (approved) | john_doe | student123 |
| Student (pending) | jane_smith | student123 |

## Architecture (8 Django Apps)
- **accounts** — Registration, Email OTP, Social Auth (Google/GitHub/LinkedIn), Cookie Consent
- **courses** — Course catalog, modules, exercises (quiz/text/code/file), enrollment, progress
- **dashboard** — Role-based dashboards (Student, Mentor, Admin) with full CRUD
- **certificates** — Auto-generated PDF certificates with public verification
- **notifications** — Real-time notification system with AJAX polling
- **messaging** — Direct messaging between students and mentors with real-time chat
- **forum** — Community discussions with categories, threads, votes, bookmarks, solutions
- **core** — Landing page, about page, shared utilities

## Key Features

### Students
- Register → Email OTP verify → Wait for admin approval → Access courses
- Enroll in courses, work through modules and exercises
- Auto-graded quizzes + mentor-graded text/code/file submissions
- Progress tracking with visual progress bars
- Download PDF certificates on completion
- Message mentors directly
- Participate in community forum

### Mentors
- Dashboard with all assigned courses
- Student analytics (progress, scores, completion rates)
- Grade individual or bulk submissions with feedback
- Send announcements to all enrolled students
- Course analytics with module-level breakdown
- Direct messaging with students
- Forum moderation (pin, lock, mark solutions)

### Admin
- Approve/reject student registrations
- Create mentor accounts
- Full course builder (courses → modules → exercises)
- Platform statistics and user management

### Community Forum
- 8 categories (ML, Deep Learning, NLP, Computer Vision, etc.)
- Thread creation with tags
- Nested replies, upvote/downvote system
- Mark answers as solutions
- Bookmark threads
- Search across discussions
- Pin/lock threads (moderators)

### Technical
- Dark/Light mode (dark blue+gold / white+blue)
- Responsive design with mobile sidebar
- REST API (Django REST Framework)
- Social auth (Google, GitHub, LinkedIn via django-allauth)
- AJAX notification polling (30s)
- Real-time chat message polling (5s)
- Cookie consent (GDPR)
- Password reset via email
- Custom 404/500 error pages
- 1762 lines of custom CSS, 220 lines of JS

## Tech Stack
Django 5, Django REST Framework, django-allauth, ReportLab (PDF), SQLite, HTML/CSS/JS
