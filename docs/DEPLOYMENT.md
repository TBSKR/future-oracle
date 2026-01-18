# 🚀 Deployment Guide

This guide provides instructions for deploying the FutureOracle application to a production environment. The recommended setup involves a combination of Streamlit Community Cloud for the frontend and a cheap Virtual Private Server (VPS) for the backend agent execution.

---

## 1. Deployment Architecture

-   **Frontend/Dashboard:** Deployed on **Streamlit Community Cloud**. It's free, easy to set up, and handles hosting the interactive dashboard.
-   **Backend/Agents:** Runs on a **Linux VPS** (e.g., Hetzner, DigitalOcean, Linode). This ensures 24/7 execution of the scheduled agent workflows (cron jobs).
-   **Database:** A **SQLite** file located on the VPS, providing persistent storage for portfolio data and analysis results.
-   **Code Repository:** **GitHub** hosts the codebase, and deployments are triggered from the `main` branch.

```
                               +-------------------------+
                               |  Streamlit Community    |
                               |         Cloud           |
                               +-----------+-------------+
                                           ^
                                           | HTTPS
                                           v
+-----------------+            +-----------+-------------+
|      User       | <--------> |   Streamlit Dashboard   |
+-----------------+            +-------------------------+
                                           ^
                                           | API Calls (Future)
                                           v
+-----------------+            +-----------+-------------+
|       VPS       |            |   Backend Agents        |
| (Hetzner €5/mo) | <--------> | (Cron Jobs, CrewAI)     |
+-----------------+            +-----------+-------------+
                                           ^
                                           | Read/Write
                                           v
                               +-----------+-------------+
                               |      SQLite DB          |
                               +-------------------------+
```

---

## 2. VPS Setup (Hetzner)

We recommend a basic cloud server from Hetzner (e.g., CX11 or CPX11) which costs around €5/month.

### Step 1: Create and Secure the Server

1.  **Sign up** for a Hetzner Cloud account.
2.  **Create a new project** and **add a new server**.
    -   **Location:** Choose a location (e.g., Falkenstein).
    -   **Image:** Ubuntu 22.04.
    -   **Type:** Shared vCPU (CX11 or CPX11 is sufficient).
    -   **SSH Key:** Add your public SSH key for secure access.
3.  **Connect to the server** via SSH:
    ```bash
    ssh root@<your_server_ip>
    ```
4.  **Create a non-root user** and give it sudo privileges:
    ```bash
    adduser futureoracle
    usermod -aG sudo futureoracle
    ```
5.  **Copy your SSH key** to the new user:
    ```bash
    rsync --archive --chown=futureoracle:futureoracle ~/.ssh /home/futureoracle
    ```
6.  **Log in as the new user**:
    ```bash
    ssh futureoracle@<your_server_ip>
    ```

### Step 2: Install Dependencies

1.  **Update the system**:
    ```bash
    sudo apt update && sudo apt upgrade -y
    ```
2.  **Install Python 3.11 and venv**:
    ```bash
    sudo apt install python3.11 python3.11-venv python3-pip git -y
    ```
3.  **Install Git**:
    ```bash
    sudo apt install git -y
    ```

### Step 3: Clone the Project

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/TBSKR/future-oracle.git
    cd future-oracle
    ```
2.  **Create a virtual environment**:
    ```bash
    python3.11 -m venv venv
    source venv/bin/activate
    ```
3.  **Install Python dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

### Step 4: Configure the Environment

1.  **Create the `.env` file**:
    ```bash
    cp config/.env.example config/.env
    ```
2.  **Edit the `.env` file** with your production API keys and settings:
    ```bash
    nano config/.env
    ```
    -   Fill in `XAI_API_KEY`, `NEWSAPI_KEY`, `DISCORD_WEBHOOK_URL`, etc.
    -   Set `PAPER_TRADING=false` if you are connecting to a live broker.

### Step 5: Set Up Cron Jobs

1.  **Open the crontab editor**:
    ```bash
    crontab -e
    ```
2.  **Add the scheduled tasks**. These commands run the agent workflows using the virtual environment's Python interpreter.

    ```cron
    # FutureOracle Cron Jobs
    # Make sure to use absolute paths

    # Daily intelligence run at 9 AM server time
    0 9 * * * /home/futureoracle/future-oracle/venv/bin/python /home/futureoracle/future-oracle/scripts/run_daily.py >> /home/futureoracle/future-oracle/logs/cron.log 2>&1

    # Weekly intelligence report on Sunday at 8 PM server time
    0 20 * * 0 /home/futureoracle/future-oracle/venv/bin/python /home/futureoracle/future-oracle/scripts/run_weekly.py >> /home/futureoracle/future-oracle/logs/cron.log 2>&1
    ```

3.  **Create the log file** and set permissions:
    ```bash
    mkdir -p /home/futureoracle/future-oracle/logs
    touch /home/futureoracle/future-oracle/logs/cron.log
    ```

Your backend is now live. The agents will run automatically on the schedule you've defined.

---

## 3. Frontend Deployment (Streamlit Cloud)

1.  **Push your project to GitHub**.
2.  **Sign up** for a [Streamlit Community Cloud](https://streamlit.io/cloud) account (you can sign in with your GitHub account).
3.  **Click "New app"** and select your `future-oracle` repository.
4.  **Configure the deployment**:
    -   **Repository:** `TBSKR/future-oracle`
    -   **Branch:** `main`
    -   **Main file path:** `src/app.py`
    -   **App URL:** Choose a custom URL (e.g., `futureoracle.streamlit.app`).
5.  **Add your secrets**:
    -   Click on **"Advanced settings..."**.
    -   In the **"Secrets"** section, copy and paste the contents of your local `config/.env` file. This is crucial for the Streamlit app to access APIs if needed (though most heavy lifting is done by the backend).
6.  **Click "Deploy!"**.

Streamlit will build and deploy your application. You'll have a public URL to your dashboard.

---

## 4. Maintenance and Updates

### Updating the Application

1.  **Pull the latest changes** on your local machine:
    ```bash
    git pull origin main
    ```
2.  **Make your changes** (e.g., update agent logic, add a new chart to the dashboard).
3.  **Push the changes** back to GitHub:
    ```bash
    git add .
    git commit -m "Your update message"
    git push origin main
    ```

-   **Streamlit Frontend:** Streamlit Cloud will automatically detect the push to the `main` branch and redeploy your dashboard.
-   **VPS Backend:** SSH into your VPS and pull the latest changes:
    ```bash
    ssh futureoracle@<your_server_ip>
    cd future-oracle
    git pull origin main
    pip install -r requirements.txt # Re-install dependencies if changed
    ```
    The cron jobs will automatically use the updated code on their next run.

### Monitoring

-   **Check the cron log** for any errors from the backend agents:
    ```bash
    tail -f /home/futureoracle/future-oracle/logs/cron.log
    ```
-   **Check the Streamlit dashboard** to ensure it's rendering correctly.
-   **Monitor your email and Discord** for notifications from the `Reporter` agent.
