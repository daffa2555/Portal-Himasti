# TODO - Upgrade Himasti Portal

- [x] Audit struktur repo & dependensi (app.py utama, absensi logic ada di absensi_himasti.py terpisah)
- [x] Edit `app.py`: cache & lazy-load data per tab (kader/keuangan/absensi/arsip) biar performa naik
- [ ] Edit `app.py`: integrasi panel absensi publik saat `logged_in == False` (camera QR + input NIM manual)
- [ ] Edit `app.py`: port fungsi inti absensi dari `absensi_himasti.py` (normalize_nim, decode QR, save_absen, has_absen_today)
- [ ] Edit `app.py`: harden rendering HTML (pastikan sanitize/escape sebelum `unsafe_allow_html=True`)
- [ ] Jalankan Streamlit & tes alur login + absensi (scan QR/manual/sudah absen hari ini)
- [ ] (Opsional) Siapkan SQL DB-level unique constraint untuk anti-duplikat absensi

