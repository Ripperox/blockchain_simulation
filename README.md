---

## **📜 Blockchain Simulator**
A **simple blockchain simulator** built with **Flask** that allows users to mine new blocks dynamically. This project includes a **modern UI** and supports **Dockerization** for seamless deployment.  
![image](https://github.com/user-attachments/assets/7738df2a-f807-470a-a2d4-7c4cc345b7be)


---

## **🚀 Features**
✅ Mine new blocks dynamically  
✅ Modern & sleek **dark-themed UI**  
✅ Blockchain visualization  
✅ Dockerized for easy deployment  
✅ REST API for blockchain interactions  

---

## **🛠 Installation & Usage**

### **🔹 Option 1: Run with Docker (Recommended)**
Make sure **Docker** is installed and running.

1️⃣ **Clone the repository:**  
```sh
git clone https://github.com/Ripperox/blockchain-app.git
cd blockchain-app
```
  
2️⃣ **Build the Docker image:**  
```sh
docker build -t blockchain-app .
```

3️⃣ **Run the Docker container:**  
```sh
docker run -p 5000:5000 blockchain-app
```

4️⃣ **Access the app in your browser:**  
Open **[http://localhost:5000](http://localhost:5000)** 🚀  

---

### **🔹 Option 2: Run Locally Without Docker**
Make sure you have **Python 3.8+** installed.  

1️⃣ **Create a virtual environment (optional but recommended)**  
```sh
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

2️⃣ **Install dependencies**  
```sh
pip install -r requirements.txt
```

3️⃣ **Run the application**  
```sh
python app.py
```

4️⃣ Open **[http://localhost:5000](http://localhost:5000)** in your browser.

---

## **📡 API Endpoints**
| Method | Endpoint          | Description               |
|--------|------------------|---------------------------|
| GET    | `/blocks`        | Get all mined blocks      |
| POST   | `/mine`          | Mine a new block          |

---

## **📄 File Structure**
```
blockchain-app/
│── app.py                # Flask backend
│── Dockerfile            # Docker build instructions
│── requirements.txt      # Python dependencies
│── templates/
│   ├── index.html        # Frontend UI
│── static/
│   ├── style.css         # UI styling
│   ├── script.js         # Frontend logic
│── README.md             # This file
```

---


## **🤝 Contribution**
Feel free to **fork** this repo, create a new branch, and submit a **pull request**.  
---

