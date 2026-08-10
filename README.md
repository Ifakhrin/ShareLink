# ShareLink - Internal File Transfer System

Aplikasi web pertukaran file sementara (temporary file transfer) antar pengguna internal secara aman melalui antarmuka web. File disimpan sementara di server lokal dan **otomatis dihapus permanen dari storage** setelah pengunduhan berhasil, saat dibatalkan pengirim, atau saat mencapai batas waktu kadaluwarsa (24 jam).

---

## 🚀 Fitur Utama

1. **Pengiriman File 1-ke-1**: Pengguna dapat mengirim satu atau beberapa file kepada tepat satu pengguna lain.
2. **Auto-Delete Setelah Download**: File fisik langsung dihapus dari disk server segera setelah pengunduhan oleh penerima selesai dikirim secara utuh.
3. **Batas Ukuran & Validasi**:
   - Maksimum **1 GB** per file.
   - Maksimum **2 GB** total per transfer.
   - Penolakan file kosong (0 byte).
4. **Kode Transfer Cryptographically Secure**: Format tampilan `XXXX-XXXXX-XX` yang unik dan ber-entropi tinggi.
5. **Role & Otorisasi Ketat**:
   - **Sender**: Hanya dapat melihat transfer miliknya dan membatalkan transfer miliknya yang masih aktif.
   - **Receiver**: Hanya dapat melihat transfer yang ditujukan kepadanya dan mendownload file terkait.
   - **Admin**: Dapat melihat seluruh data transfer, audit log aktivitas, dan menghapus transfer.
6. **Masa Berlaku (Expiration 24 Jam)**: File yang belum diunduh setelah 24 jam akan otomatis ditandai `EXPIRED` dan file fisiknya dibersihkan.
7. **Audit Log Trail**: Mencatat setiap aktivitas penting (`LOGIN`, `FILE_UPLOADED`, `DOWNLOAD_COMPLETED`, `TRANSFER_CANCELLED`, `FILE_DELETED`, dll).

---

## 🛠️ Persyaratan Sistem (Requirements)

- **Python**: 3.9 / 3.10 / 3.11 / 3.12+
- **Pip**: Manager paket Python standard
- **OS**: Windows / Linux / macOS

---

## 🔧 Instalasi & Setup Lokal

### 1. Clone & Buka Repositori
```bash
git clone <repository_url>
cd ShareLink
```

### 2. Buat & Aktifkan Virtual Environment
Di Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate
```

Di Linux / macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Konfigurasi Environment (`.env`)
Salin berkas `.env.example` menjadi `.env`:
```bash
cp .env.example .env
```
Isi konfigurasi pada `.env` (secara default sudah dikonfigurasi untuk pengujian lokal):
```env
SECRET_KEY=dev-secret-key-sharelink-internal-system-38917491
DATABASE_URL=sqlite:///app.db
MAX_FILE_SIZE=1073741824
MAX_TRANSFER_SIZE=2147483648
FILE_EXPIRATION_HOURS=24
UPLOAD_FOLDER=storage
```

### 5. Inisialisasi Database & Seed Data
Jalankan skrip seeder untuk membuat tabel database SQLite dan mengisi akun sampel development:
```bash
python seed.py
```

---

## 🔐 Akun Development (Local Seed Data)

> [!WARNING]
> Kredensial di bawah ini khusus digunakan untuk kebutuhan pengujian dan pengembangan lokal. JANGAN gunakan password default ini pada lingkungan produksi!

- **Admin Account**:
  - Username: `admin`
  - Password: `Admin123!`
  - Role: `admin`

- **User 1 (Sender)**:
  - Username: `user1`
  - Password: `User123!`
  - Role: `user`

- **User 2 (Receiver)**:
  - Username: `user2`
  - Password: `User123!`
  - Role: `user`

---

## 🏃 Cara Menjalankan Aplikasi

Jalankan server aplikasi Flask:
```bash
python run.py
```
Buka peramban (browser) dan akses:
`http://127.0.0.1:5000`

### Menjalankan Cleanup Manual Expired Transfer
Untuk membersihkan transfer yang sudah kadaluwarsa (> 24 jam) secara manual melalui CLI:
```bash
python run.py cleanup
```
atau menggunakan CLI Flask:
```bash
flask cleanup-expired
```

---

## 🧪 Menjalankan Automated Tests

Seluruh 20 skenario pengujian unit test dapat dijalankan dengan command `pytest`:
```bash
pytest
```
Untuk melihat output detail per skenario:
```bash
pytest -v
```

---

## 📂 Struktur Project

```
ShareLink/
├── app/
│   ├── __init__.py         # App factory & custom error handlers
│   ├── config.py           # Konfigurasi aplikasi dari environment
│   ├── models/             # SQLAlchemy ORM Models
│   │   ├── __init__.py
│   │   ├── user.py         # Model Pengguna & Role
│   │   ├── transfer.py     # Model Transfer & Status
│   │   ├── file.py         # Model Metadata File & Lifecycle Status
│   │   └── transfer_log.py # Model Audit Trail Logs
│   ├── routes/             # Controllers / Blueprints
│   │   ├── auth.py         # Route Login & Logout
│   │   ├── dashboard.py    # Route Dashboard Utama (File Masuk & Terkirim)
│   │   ├── transfer.py     # Route Send, Detail, Download, & Cancel
│   │   └── admin.py        # Route Admin Monitoring & Audit Logs
│   ├── services/           # Business Logic Layer
│   │   ├── auth_service.py     # Session & Auth Decorator Helpers
│   │   ├── transfer_service.py # Core transfer lifecycle & code generator
│   │   ├── file_service.py     # Storage, sanitization & stream auto-delete
│   │   └── log_service.py      # Logger audit trail
│   ├── templates/          # Jinja2 HTML Templates
│   │   ├── base.html
│   │   ├── auth/
│   │   │   └── login.html
│   │   ├── dashboard/
│   │   │   └── index.html
│   │   ├── transfer/
│   │   │   ├── send.html
│   │   │   ├── detail.html
│   │   │   └── success.html
│   │   └── admin/
│   │       └── index.html
│   └── static/             # Assets Statis
│       ├── css/
│       │   └── style.css   # Dark Glassmorphism CSS Design System
│       └── js/
│           ├── upload.js   # XHR Upload progress & multi-file preview
│           └── main.js     # Clipboard helper & dialog confirmation
├── storage/
│   └── .gitkeep            # Folder penyimpanan fisik file (non-public)
├── tests/                  # Pytest Automated Test Suite (20 Scenarios)
│   ├── conftest.py
│   ├── test_auth.py
│   └── test_transfer.py
├── seed.py                 # Skrip seeder database awal
├── run.py                  # Runner utama & CLI command
├── requirements.txt        # Daftar dependency Python
├── .env.example            # Template konfigurasi environment variable
├── .gitignore              # Aturan Git ignore
└── README.md               # Dokumentasi proyek
```
