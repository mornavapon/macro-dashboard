# Macro Dashboard

เว็บแอปรวมภาพรวมเศรษฐกิจมหภาคไว้ในที่เดียว มี 3 หน้า ปัดซ้าย/ขวาเพื่อเปลี่ยนหน้า

ลิ้งค์ไปยังเอไอที่สร้าง
https://claude.ai/chat/319d9b70-978e-435a-ad71-1882f0ce5a3f

ลิ้งค์ไปยังหน้าเวปแอป
https://mornavapon.github.io/macro-dashboard/

| หน้า | เนื้อหา | สถานะ |
|---|---|---|
| 1. ดัชนีโลก | S&P 500, NASDAQ, SET, HSCEI, SSE Composite, VN-Index: ระดับดัชนี / Market Cap / P/E / P/BV / วันที่ของข้อมูล | ✅ เฟส 1 |
| 2. อเมริกา | GDP, ตารางประชุมเฟด, CPI | 🚧 |
| 3. ไทย | GDP, ตารางประชุม กนง., เงินเฟ้อ, ส่งออก | 🚧 |

## โครงสร้าง

```
index.html, style.css, app.js        หน้าเว็บ (GitHub Pages)
scripts/fetch_indices.py             ดึงข้อมูลหน้า 1 (Python มาตรฐาน ไม่ต้องติดตั้งเพิ่ม)
.github/workflows/update-indices.yml รันดึงข้อมูลอัตโนมัติทุก 3 ชม. + กดรันเองได้
data/indices.json                    ข้อมูลที่หน้าเว็บอ่าน
data/debug/                          ผลดิบจากแต่ละแหล่ง ไว้ตรวจสอบเวลาดึงไม่สำเร็จ
```

แต่ละส่วนแยกกัน: แต่ละดัชนีและแต่ละช่องข้อมูลดึงแยกกัน ถ้าแหล่งไหนพัง หน้าเว็บจะขึ้นว่า
**"ดึงข้อมูลไม่สำเร็จ"** เฉพาะช่องนั้น ถ้าเคยดึงได้มาก่อน จะแสดงค่าเก่าพร้อมป้าย **"⚠ ข้อมูลเก่า"**

## การติดตั้ง (ครั้งแรก)

1. สร้าง repo ใหม่บน GitHub เป็น **Public** (GitHub Pages ฟรีใช้ได้กับ Public เท่านั้น)
2. **Add file → Upload files** แล้วลากไฟล์และโฟลเดอร์ทั้งหมดในโฟลเดอร์นี้ไปวาง → Commit
3. **Settings → Pages** → Source: *Deploy from a branch* → Branch: `main` / `(root)` → Save
4. **Settings → Actions → General** → Workflow permissions: *Read and write permissions* → Save
5. **Actions** → *อัปเดตข้อมูลดัชนี (หน้า 1)* → **Run workflow**
6. เปิดเว็บที่ `https://<ชื่อผู้ใช้>.github.io/<ชื่อ repo>/`
