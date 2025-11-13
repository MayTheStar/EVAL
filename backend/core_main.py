# main.py
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from core.database import engine, Base, get_db
from core.core_config import settings
from core import models

# إنشاء كل الجداول إذا لم تكن موجودة
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    debug=settings.DEBUG
)

# ================= ROUTES: USERS ===================
@app.post("/users/", response_model=dict)
def create_user(user_data: dict, db: Session = Depends(get_db)):
    from sqlalchemy.exc import IntegrityError
    try:
        new_user = models.User(**user_data)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return {"user": {"user_id": str(new_user.user_id), "session_id": new_user.session_id}}
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/users/", response_model=list)
def list_users(db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    return [{"user_id": str(u.user_id), "session_id": u.session_id, "email": u.email} for u in users]

@app.get("/users/{user_id}", response_model=dict)
def get_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": str(user.user_id), "session_id": user.session_id, "email": user.email}

@app.delete("/users/{user_id}", response_model=dict)
def delete_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"status": "deleted"}

# ================= ROUTES: PROJECTS ===================
@app.post("/projects/", response_model=dict)
def create_project(project_data: dict, db: Session = Depends(get_db)):
    new_project = models.Project(**project_data)
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return {"project_id": str(new_project.project_id), "project_name": new_project.project_name}

@app.get("/projects/", response_model=list)
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(models.Project).all()
    return [{"project_id": str(p.project_id), "project_name": p.project_name, "user_id": str(p.user_id)} for p in projects]

@app.get("/projects/{project_id}", response_model=dict)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project_id": str(project.project_id), "project_name": project.project_name, "user_id": str(project.user_id)}

@app.delete("/projects/{project_id}", response_model=dict)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
    return {"status": "deleted"}

# ================= ROUTES: RFP DOCUMENTS ===================
@app.post("/rfps/", response_model=dict)
def create_rfp(rfp_data: dict, db: Session = Depends(get_db)):
    new_rfp = models.RFPDocument(**rfp_data)
    db.add(new_rfp)
    db.commit()
    db.refresh(new_rfp)
    return {"rfp_id": str(new_rfp.rfp_id), "filename": new_rfp.filename}

@app.get("/rfps/", response_model=list)
def list_rfps(db: Session = Depends(get_db)):
    rfps = db.query(models.RFPDocument).all()
    return [{"rfp_id": str(r.rfp_id), "filename": r.filename, "project_id": str(r.project_id)} for r in rfps]

@app.get("/rfps/{rfp_id}", response_model=dict)
def get_rfp(rfp_id: str, db: Session = Depends(get_db)):
    rfp = db.query(models.RFPDocument).filter(models.RFPDocument.rfp_id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
    return {"rfp_id": str(rfp.rfp_id), "filename": rfp.filename, "project_id": str(rfp.project_id)}

@app.delete("/rfps/{rfp_id}", response_model=dict)
def delete_rfp(rfp_id: str, db: Session = Depends(get_db)):
    rfp = db.query(models.RFPDocument).filter(models.RFPDocument.rfp_id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
    db.delete(rfp)
    db.commit()
    return {"status": "deleted"}

# ================= ROUTES: VENDOR DOCUMENTS ===================
@app.post("/vendors/", response_model=dict)
def create_vendor_doc(vendor_data: dict, db: Session = Depends(get_db)):
    new_vendor = models.VendorDocument(**vendor_data)
    db.add(new_vendor)
    db.commit()
    db.refresh(new_vendor)
    return {"vendor_doc_id": str(new_vendor.vendor_doc_id), "vendor_name": new_vendor.vendor_name}

@app.get("/vendors/", response_model=list)
def list_vendor_docs(db: Session = Depends(get_db)):
    vendors = db.query(models.VendorDocument).all()
    return [{"vendor_doc_id": str(v.vendor_doc_id), "vendor_name": v.vendor_name, "project_id": str(v.project_id)} for v in vendors]

@app.get("/vendors/{vendor_doc_id}", response_model=dict)
def get_vendor_doc(vendor_doc_id: str, db: Session = Depends(get_db)):
    vendor = db.query(models.VendorDocument).filter(models.VendorDocument.vendor_doc_id == vendor_doc_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor document not found")
    return {"vendor_doc_id": str(vendor.vendor_doc_id), "vendor_name": vendor.vendor_name, "project_id": str(vendor.project_id)}

@app.delete("/vendors/{vendor_doc_id}", response_model=dict)
def delete_vendor_doc(vendor_doc_id: str, db: Session = Depends(get_db)):
    vendor = db.query(models.VendorDocument).filter(models.VendorDocument.vendor_doc_id == vendor_doc_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor document not found")
    db.delete(vendor)
    db.commit()
    return {"status": "deleted"}
