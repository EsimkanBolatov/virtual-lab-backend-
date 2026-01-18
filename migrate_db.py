# backend/migrate_db.py
import sqlite3
import os

def migrate_database():
    db_path = "virtual_lab.db"
    
    if not os.path.exists(db_path):
        print("База табылмады. Жаңа база құрылады.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Бағанның бар екенін тексеру
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'hashed_password' not in columns:
            print("🔄 hashed_password бағанын қосу...")
            cursor.execute("ALTER TABLE users ADD COLUMN hashed_password TEXT")
            conn.commit()
            print("✅ Миграция сәтті аяқталды!")
        else:
            print("✅ База жаңартылған")
            
    except Exception as e:
        print(f"❌ Қате: {e}")
        print("\n💡 Шешім: Ескі базаны өшіріп, қайта құрыңыз:")
        print("   rm virtual_lab.db")
        print("   python main.py")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()