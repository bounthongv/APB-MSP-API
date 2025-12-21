from sqlalchemy import Column, String, Integer, Date, DECIMAL, Text, CLOB
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from typing import Optional

Base = declarative_base()


class Section(Base):
    __tablename__ = "section"
    
    sec_id = Column(String(50), primary_key=True, nullable=False)
    sec_name = Column(String(100), nullable=True)
    sec_name_eng = Column(String(100), nullable=True)
    sec_remark = Column(String(255), nullable=True)


class Department(Base):
    __tablename__ = "department"
    
    dep_id = Column(String(50), primary_key=True, nullable=False)
    dep_name = Column(String(100), nullable=True)
    dep_name_eng = Column(String(100), nullable=True)
    dep_remark = Column(String(255), nullable=True)
    sec_id = Column(String(100), nullable=False)


class Place(Base):
    __tablename__ = "place"
    
    p_id = Column(String(255), primary_key=True, nullable=False)
    p_name = Column(String(100), nullable=True)
    p_name_eng = Column(String(100), nullable=True)
    p_remark = Column(String(255), nullable=True)


class Property(Base):
    __tablename__ = "property"
    
    pro_id = Column(String(50), primary_key=True, nullable=False)
    pro_name = Column(String(200), nullable=True)  # Updated to VARCHAR2(200)
    pro_name_eng = Column(String(100), nullable=True)
    pro_acc1 = Column(String(255), nullable=True)
    pro_acc2 = Column(String(255), nullable=True)
    pro_acc3 = Column(String(255), nullable=True)
    pro_acc4 = Column(String(255), nullable=True)
    pro_acc5 = Column(String(255), nullable=True)
    pro_acc_id = Column(String(255), nullable=True)


class AssetType(Base):
    __tablename__ = "type"
    
    type_id = Column(String(255), primary_key=True, nullable=False)
    type_name = Column(String(100), nullable=True)
    type_name_eng = Column(String(100), nullable=True)
    type_remark = Column(String(255), nullable=True)


class Office(Base):
    __tablename__ = "office"
    
    off_id = Column(String(100), primary_key=True, nullable=False)
    off_name1 = Column(String(255), nullable=True)
    off_address1 = Column(String(255), nullable=True)
    off_address2 = Column(String(100), nullable=True)
    off_tel = Column(String(100), nullable=True)
    off_email = Column(String(100), nullable=True)
    off_tee = Column(String(100), nullable=True)
    off_s1 = Column(String(100), nullable=True)
    off_s2 = Column(String(100), nullable=True)
    off_s3 = Column(String(100), nullable=True)
    off_s4 = Column(String(100), nullable=True)
    off_s5 = Column(String(100), nullable=True)
    off_name2 = Column(String(255), nullable=True)
    off_address3 = Column(String(100), nullable=True)
    off_address4 = Column(String(100), nullable=True)
    off_fax = Column(String(100), nullable=True)
    off_web = Column(String(100), nullable=True)
    off_sat = Column(String(100), nullable=True)
    off_st1 = Column(String(100), nullable=True)
    off_st2 = Column(String(100), nullable=True)
    off_st3 = Column(String(100), nullable=True)
    off_st4 = Column(String(100), nullable=True)
    off_st5 = Column(String(100), nullable=True)


class Asset(Base):
    __tablename__ = "treasures"
    
    tre_id = Column(String(255), primary_key=True, nullable=False)
    sec_id = Column(String(100), nullable=False)
    dep_id = Column(String(100), nullable=False)
    pro_id = Column(String(100), nullable=False)
    tre_sup_name = Column(String(100), nullable=True)
    tre_name = Column(String(100), nullable=True)
    tre_name_eng = Column(String(100), nullable=True)
    type_id = Column(String(100), nullable=True)
    tre_juk = Column(String(100), nullable=True)
    p_id = Column(String(100), nullable=True)
    tre_num = Column(String(100), nullable=True)
    tre_barcode = Column(String(100), nullable=True)
    tre_acc = Column(String(100), nullable=True)
    tre_acc_id = Column(String(100), nullable=True)
    tre_bud = Column(String(100), nullable=True)
    tre_no = Column(String(100), nullable=True)
    tre_tung = Column(String(100), nullable=True)
    tre_gis = Column(String(100), nullable=True)
    tre_mm = Column(String(100), nullable=True)
    tre_sale_date = Column(Date, nullable=True)
    tre_sts_box = Column(String(10), nullable=True)
    tre_use_date = Column(Date, nullable=True)
    tre_price = Column(DECIMAL(12, 2), nullable=True)
    tre_cur = Column(String(100), nullable=True)
    tre_qty = Column(Integer, nullable=True)  # Changed from Integer to match NUMBER
    tre_unit = Column(String(100), nullable=True)
    tre_price_ogn = Column(DECIMAL(12, 2), nullable=True)
    tre_ex = Column(DECIMAL(12, 2), nullable=True)
    tre_price_kip = Column(DECIMAL(12, 2), nullable=True)
    tre_qty2 = Column(Integer, nullable=True)  # Changed from Integer to match NUMBER
    tre_qty_year = Column(DECIMAL(12, 2), nullable=True)
    tre_qty_month = Column(DECIMAL(12, 2), nullable=True)
    tre_date_succ = Column(String(100), nullable=True)
    tre_remark = Column(String(255), nullable=True)
    tre_finit_date = Column(Date, nullable=True)
    tre_today = Column(String(255), nullable=True)
    tre_qty_day = Column(DECIMAL(12, 2), nullable=True)


class Inventory(Base):
    __tablename__ = "inventory"
    
    iv_id = Column(String(255), primary_key=True, nullable=False)
    tre_id = Column(String(100), nullable=False)
    iv_price1 = Column(DECIMAL(12, 2), nullable=False)
    iv_price2 = Column(DECIMAL(12, 2), nullable=False)
    iv_price3 = Column(DECIMAL(12, 2), nullable=False)
    iv_name = Column(String(255), nullable=True)
    iv_remark = Column(String(255), nullable=True)
    iv_date = Column(Date, nullable=False)


class User(Base):
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    username = Column(String(255), nullable=False)
    off_id = Column(String(50), nullable=False)
    status = Column(String(100), nullable=False)
    res = Column(String(255), nullable=False)
    password = Column(CLOB, nullable=False)  # Changed from Text to CLOB
    menu_id = Column(String(255), nullable=True)
    fname = Column(String(100), nullable=False)
