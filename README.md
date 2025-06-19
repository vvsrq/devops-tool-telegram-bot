Hello!!
This is a Telegram server monitoring bot written in Python. It integrates with Prometheus and uses Linux system utilities to provide real-time information about the infrastructure.

The bot is designed to work with a specific authorized chat (by chat_id) and performs the following functions:
Getting metrics from Prometheus: RPS, response time, 5xx errors, CPU and memory load. Uses Prometheus HTTP API.

Network monitoring: /netstat — active connections (ss -tunap), output as a readable report and sending as a file. /traffic — network traffic (via vnstat) for the current day. /topips — top IP addresses by number of connections (netstat + awk + sort).

Access protection: All commands work only for allowed chat_id (ALLOW_CHAT_ID). 

Error handling and logging: Logging via logging. Sending errors to the chat when commands fail.

Usage:
    For DevOps engineers to monitor remote servers.
    
    Easy monitoring without having to log in to the server via SSH.
    
    Integration with monitoring and alerting systems.

Possible improvements:
    Support for authentication with a password or token for different users.
    
    Expandable to a full alerting system with webhook notifications.
    
    Adding metrics visualization (graphs from Prometheus).
    
    Schedule automatic reports.

Reminder
Create an .env file and put
    TELEGRAM_API_KEY = 
    PROMETHEUS_URL = 
    ALLOW_CHAT_ID= int
There

Also create a report.txt file in the root
