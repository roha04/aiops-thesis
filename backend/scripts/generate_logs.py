"""Generate synthetic logs for training and testing"""

import random
from datetime import datetime, timedelta
from db.config import SessionLocal, engine
from db.models import TrainingData, Base

# Initialize database
Base.metadata.create_all(bind=engine)

# ==================== NORMAL LOGS ====================
NORMAL_LOGS = [
    "INFO: Build started for branch main",
    "INFO: Running unit tests...",
    "INFO: Tests passed (245/245)",
    "INFO: Building Docker image...",
    "INFO: Pushing to registry...",
    "INFO: Deployment initiated",
    "INFO: Health checks passing",
    "INFO: Service started successfully",
    "INFO: Connected to database",
    "INFO: Cache warmed up",
    "INFO: Configuration loaded",
    "INFO: Listening on port 8080",
    "INFO: Request processed in 45ms",
    "INFO: Database query completed",
    "INFO: Cache hit rate: 92%",
    "INFO: All services up and running",
    "INFO: Backup completed successfully",
    "INFO: Load balancer health check OK",
    "INFO: API response time: 125ms",
    "INFO: Memory usage: 45%",
    "INFO: CPU usage: 22%",
    "INFO: Disk usage: 65%",
]

# ==================== WARNING LOGS ====================
WARNING_LOGS = [
    "WARNING: High memory usage detected (85%)",
    "WARNING: CPU usage spike detected (92%)",
    "WARNING: Slow database query (5.2s)",
    "WARNING: Deprecated API endpoint used",
    "WARNING: Missing cache entries",
    "WARNING: Disk usage high (78%)",
    "WARNING: Thread pool exhausted",
    "WARNING: Rate limit approaching",
    "WARNING: Connection pool low",
    "WARNING: Response time degradation observed",
    "WARNING: Increased latency: 2.5s",
    "WARNING: Database connection pool usage: 85%",
]

# ==================== ERROR/ANOMALY LOGS ====================
ANOMALY_LOGS = [
    # Database errors
    "ERROR: Database connection timeout after 30s",
    "ERROR: Database connection lost",
    "ERROR: SQL query failed: timeout",
    "ERROR: Connection refused from database server",
    "ERROR: Cannot acquire database connection",
    "ERROR: Database pool exhausted",
    "ERROR: Transaction rollback failed",
    
    # Authentication errors
    "ERROR: Failed to authenticate with credentials",
    "ERROR: Invalid API key provided",
    "ERROR: Authorization header missing",
    "ERROR: JWT token expired",
    "ERROR: LDAP authentication failed",
    
    # Memory/Resource errors
    "ERROR: Memory allocation failed - OutOfMemoryError",
    "ERROR: Heap space exceeded",
    "ERROR: Cannot allocate 2GB memory",
    "ERROR: GC overhead limit exceeded",
    
    # Port/Network errors
    "ERROR: Port 5432 already in use",
    "ERROR: Cannot bind to port 8080",
    "ERROR: Network unreachable to external service",
    "ERROR: Connection refused by host",
    "ERROR: Socket timeout",
    "ERROR: DNS resolution failed",
    
    # Configuration/File errors
    "ERROR: File not found: config.yml",
    "ERROR: Configuration parsing failed",
    "ERROR: Invalid configuration syntax",
    "ERROR: Missing required environment variable",
    
    # SSL/Security errors
    "ERROR: SSL certificate verification failed",
    "ERROR: Certificate expired",
    "ERROR: Handshake protocol error",
    
    # Deployment errors
    "ERROR: Deployment rollback initiated",
    "ERROR: Docker container crashed unexpectedly",
    "ERROR: Container start timeout",
    "ERROR: Image pull failed",
    "ERROR: Kubernetes pod evicted",
    
    # Service errors
    "ERROR: Health check failed for service",
    "ERROR: Service unavailable",
    "ERROR: Circuit breaker opened",
    "ERROR: Service dependencies missing",
    
    # Application errors
    "ERROR: Null pointer exception in module X",
    "ERROR: Index out of bounds",
    "ERROR: Stack overflow detected",
    "ERROR: Division by zero",
    "ERROR: Infinite loop detected",
    "ERROR: Fatal exception in thread pool",
    
    # System errors
    "ERROR: Disk space critical (1GB remaining)",
    "ERROR: System resource limit reached",
    "ERROR: File descriptor limit exceeded",
]

def generate_logs(normal_count: int = 500, anomaly_count: int = 200):
    """Generate synthetic logs with better variation"""
    
    db = SessionLocal()
    
    try:
        print(f"Generating {normal_count} normal logs and {anomaly_count} anomaly logs...")
        
        # Clear existing data
        db.query(TrainingData).delete()
        db.commit()
        
        # Generate normal logs (mostly normal + some warnings mixed)
        for i in range(normal_count):
            if random.random() < 0.85:  # 85% pure normal
                log_text = random.choice(NORMAL_LOGS)
            else:  # 15% warnings (still considered normal)
                log_text = random.choice(WARNING_LOGS)
            
            log = TrainingData(
                log_text=log_text,
                is_anomaly=False
            )
            db.add(log)
            
            if (i + 1) % 100 == 0:
                print(f"  Generated {i + 1} normal logs...")
        
        # Generate anomaly logs (mostly errors)
        for i in range(anomaly_count):
            if random.random() < 0.1:  # 10% warnings that lead to anomalies
                log_text = random.choice(WARNING_LOGS) + " - CRITICAL"
            else:  # 90% actual errors
                log_text = random.choice(ANOMALY_LOGS)
            
            log = TrainingData(
                log_text=log_text,
                is_anomaly=True
            )
            db.add(log)
            
            if (i + 1) % 100 == 0:
                print(f"  Generated {i + 1} anomaly logs...")
        
        db.commit()
        print(f"✅ Generated {normal_count + anomaly_count} logs total")
        
        # Show statistics
        total = db.query(TrainingData).count()
        anomalies = db.query(TrainingData).filter(TrainingData.is_anomaly == True).count()
        normal = total - anomalies
        
        print(f"\n📊 Database stats:")
        print(f"   Total logs: {total}")
        print(f"   Normal logs: {normal} ({100*normal/total:.1f}%)")
        print(f"   Anomaly logs: {anomalies} ({100*anomalies/total:.1f}%)")
        
        return total
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    generate_logs()