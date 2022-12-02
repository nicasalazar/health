import connexion, requests, yaml, json, os, logging, logging.config, sqlite3
from connexion import NoContent
import datetime
from flask_cors import CORS, cross_origin
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from base import Base
from health import Health

with open('app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())

with open('log_conf.yml', 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')

sqlite = app_config["datastore"]["filename"]
DB_ENGINE = create_engine(f"sqlite:///{sqlite}")
Base.metadata.bind = DB_ENGINE
Base.metadata.create_all(DB_ENGINE)
DB_SESSION = sessionmaker(bind=DB_ENGINE)

def create_table():
    conn = sqlite3.connect(sqlite)
    c = conn.cursor()

    c.execute('''
            CREATE TABLE health
            (id INTEGER PRIMARY KEY ASC,
            receiver VARCHAR(50) NOT NULL,
            storage VARCHAR(50) NOT NULL,
            processing VARCHAR(50) NOT NULL,
            audit VARCHAR(50) NOT NULL,
            last_updated VARCHAR(100) NOT NULL)
    ''')

    conn.commit()
    conn.close()

if os.path.exists(sqlite) == False:
    create_table()

def get_health():
    """ Periodically update health """
    logger.info("Start Periodic Processing") 

    session = DB_SESSION()

    results = session.query(Health).all()

    if not results:
        h = Health("Down",
                  "Down",
                  "Down",
                  "Down",
                  datetime.datetime.now())

        session.add(h)
        session.commit()
        session.close()
    else:
        results = session.query(Health).order_by(Health.last_updated.desc())
        last_updated = results[0].last_updated.strftime("%Y-%m-%dT%H:%M:%S")
        current_timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        receiver = results[0].receiver
        storage = results[0].storage
        processing = results[0].processing
        audit = results[0].audit

        try:
            requests.get(app_config["receiver"], timeout=5)
            receiver = "Running"
        except: 
            receiver = "Down"
            
        try:
            requests.get(app_config["storage"], timeout=5)
            storage = "Running"
        except: 
            storage = "Down"

        try:
            requests.get(app_config["processing"], timeout=5)
            processing = "Running"
        except: 
            processing = "Down"

        try:
            requests.get(app_config["audit"], timeout=5)
            audit = "Running"
        except: 
            audit = "Down"

        current_timestamp = datetime.datetime.now().strptime(current_timestamp, "%Y-%m-%dT%H:%M:%S")

        h = Health(receiver,
                    storage,
                    processing,
                    audit,
                    current_timestamp)
            
        health_dict = {
                "receiver": receiver,
                "storage": storage,
                "processing": processing,
                "audit": audit,
                "last_updated": last_updated
            }

        logger.debug(health_dict)

        session.add(h)

        session.commit()
        session.close()

        logging.info(f'End Periodic Processing')

        return health_dict, 200

def init_scheduler(): 
    sched = BackgroundScheduler(daemon=True) 
    sched.add_job(get_health,    
                  'interval', 
                  seconds=app_config['scheduler']['period_sec']) 
    sched.start()

app = connexion.FlaskApp(__name__, specification_dir="")
app.add_api("openapi.yaml", base_path="/health", strict_validation=True, validate_responses=True)
CORS(app.app)
app.app.config['CORS_HEADERS'] = 'Content-Type'

if __name__ == "__main__": 
    init_scheduler() 
    app.run(port=8120, use_reloader=False)