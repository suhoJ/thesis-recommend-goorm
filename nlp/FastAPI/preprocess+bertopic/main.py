from fastapi import FastAPI, HTTPException, Query
import preprocess 
import pandas as pd
import sqlalchemy
import logging
import preprocess
from tokenizer import DataProcessor
from bertopic_model import TopicModeler
from bertopic_model import apply_category_models
from konlpy.tag import Mecab
from eunjeon import Mecab  # mecab 둘 중 하나 되는걸로 import
# from sqlalchemy.ext.declarative import declarative_base  #2.0미만 버전
from sqlalchemy.orm import declarative_base # 2.0이상 버전 - 확인 요망
from sqlalchemy import Column, Integer, Text
from sqlalchemy.dialects.mysql import LONGTEXT
from preprocess import PreprocessedNews
from sqlalchemy import create_engine
from pydantic import BaseModel
from bertopic_model import TopicModeler, extract_top_keywords
from wordcloud_generator import generate_wordcloud

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Update this with your MySQL RDS credentials
db_username = "goorm"
db_password = "goorm1415"
db_host = "thesis-mysql.cx2cmy4wc806.ap-northeast-2.rds.amazonaws.com"
db_name = "mydatabase"
mysql_connection_string = f"mysql+mysqlconnector://{db_username}:{db_password}@{db_host}/{db_name}"

# Create a database engine
engine = sqlalchemy.create_engine(mysql_connection_string)

app = FastAPI()
mecab = Mecab()

Base = declarative_base()

class TextData(Base):
    __tablename__ = "text_data"
    text = Column(LONGTEXT)
    category = Column(Text)

@app.post("/preprocess")
def preprocess_data(start_date: str = Query(None), end_date: str = Query(None)):
    if not start_date or not end_date:
        raise HTTPException(status_code=400, detail="Start date and end date must be provided")
    
    # preprocessed_data = preprocess.preprocess_data(engine, start_date, end_date)  # 전처리 메서드 호출
    preprocessed_data = preprocess.preprocess_data(engine, 20231207, 20231207)    # 테스트용
    
    # 전처리된 데이터를 데이터베이스에서 조회
    query = "SELECT * FROM preprocessed_news"
    df = pd.read_sql_query(sql=query, con=engine)
    
    results = {}
    # DataProcessor 인스턴스 생성- db에 저장할 필요없음, DataProcessor와 TopicModeler를 분리하면 안됨.
    data_processor = DataProcessor(tagger=mecab, engine=engine, n=2)  
    # TopicModeler 인스턴스 생성, 이 때 tokenizer로 data_processor를 넘겨줌, bertopic자체에서 토큰화 진행됨. db 저장하려면 모델 다 돌리고 저장해야함.
    topic_modeler = TopicModeler(dataprocessor=data_processor, max_features=3000)

    for category in df['category'].unique():
        category_docs = df[df['category'] == category]['text'].astype(str)
        topic_model = topic_modeler.fit_model(category_docs)
        top_keywords = extract_top_keywords(topic_model)
        wordcloud_img = generate_wordcloud(topic_model)
        results[category] = {
            "top_keywords": top_keywords,
            "wordcloud": wordcloud_img
        }

    return results


@app.get("/")
async def home():
    return "Welcome to the preprocess App!"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
