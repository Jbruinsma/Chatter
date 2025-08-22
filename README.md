# Chatter

Chatter is a real-time messaging application built as a personal learning project to explore **WebSockets**, **real-time communication**, and **scalable app design**.  
It features both private and group messaging, user profiles, and basic social interactions (friends/following).  

This project represents **Version 1 (V1)** of Chatter — a foundational version designed to practice backend data structures, frontend frameworks, and real-time updates.

---

## Features

- Real-time messaging powered by WebSockets  
- Group chats with multiple participants  
- User profiles with public or private visibility  
- Social features including following and friends  

---

## Tech Stack

- **Backend**: [Python](https://www.python.org/) with [FastAPI](https://fastapi.tiangolo.com/) (WebSocket + REST endpoints)  
- **Frontend**: [Vue.js](https://vuejs.org/)  
- **Data Layer**: Custom-built **AVL Tree** structure simulating a database (Object-Oriented `User` and `Chat` classes)  

---

## Project Structure

- `backend/` → FastAPI server handling WebSockets, endpoints, and simulated database  
- `frontend/` → Vue.js application handling UI and real-time chat updates  

---

## Future Improvements

Chatter V1 is a base product designed to explore real-time app fundamentals. Planned improvements include:

- **Database Integration** — Replace AVL tree with a relational or NoSQL database once I complete Database Management coursework.  
- **Enhanced Models** — Redesign `User` and `Chat` classes to support richer features and improved scalability.  
- **Image Support** — Profile pictures and inline chat media.  
- **Encryption** — Add end-to-end encryption after completing coursework in cryptography and security.  
- **Web3 Integration** — Experimental crypto support for transactions or authentication.  
- **Production Hardening** — Authentication, deployment, and security features.  

---

## Purpose

Chatter was created as a personal learning project to:  
- Understand how real-time updates work in modern messaging/social apps  
- Gain hands-on experience with **WebSockets** and **FastAPI**  
- Practice combining **frontend frameworks (Vue)** with a custom **backend architecture**  
- Explore **data structures (AVL Trees)** as a database substitute  

This project highlights curiosity-driven development and a focus on learning core concepts of scalable applications.

---

## License

This project is for educational and portfolio purposes.  
