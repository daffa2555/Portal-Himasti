import qrcode
from supabase import create_client
import os

# --- KONEKSI SUPABASE ---
# Ambil dari Dashboard Supabase > Settings > API
URL = "https://kryzdnlrgxgjwpfnpumg.supabase.co"
KEY = "sb_publishable_9KtgzT26tgYHK6r2muVVEA_6Nx91MDF"
supabase = create_client(URL, KEY)

# Buat folder penyimpanan
folder = 'QR_Kader_HIMASTI'
if not os.path.exists(folder):
    os.makedirs(folder)

def gas_generate():
    try:
        print("🔄 Menarik data kader dari Supabase...")
        res = supabase.table("kader").select("nama, nim").execute()
        kader_list = res.data

        if not kader_list:
            print("❌ Waduh, tabel kader masih kosong Nan!")
            return

        for kader in kader_list:
            nama = kader['nama']
            nim = kader['nim']
            
            # Buat QR (Isinya NIM saja biar sinkron sama aplikasi absensi)
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(nim)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            
            # Bersihkan nama file dari karakter aneh
            nama_file = f"{nama.replace(' ', '_')}_{nim}.png"
            path_file = os.path.join(folder, nama_file)
            
            img.save(path_file)
            print(f"✅ Berhasil: {nama_file}")

        print(f"\n🚀 SELESAI! Semua QR ada di folder: {folder}")
        
    except Exception as e:
        print(f"❌ Error nih: {e}")

if __name__ == "__main__":
    gas_generate()