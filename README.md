# RRI Reporter Monitor — Gratis Online

Versi ini memakai **GitHub Pages + GitHub Actions**. Tidak perlu VPS dan tidak perlu PC menyala. GitHub Actions menjalankan scanner setiap 6 jam dan memperbarui `data.json`; GitHub Pages menampilkan dashboard.

## Setup paling mudah

1. Buat akun/login GitHub.
2. Buat repository baru, misalnya `rri-reporter-monitor`.
3. Pilih **Public** agar GitHub Pages/Actions mudah dipakai gratis.
4. Upload **semua isi folder ini** ke repository (bukan folder pembungkusnya).
5. Buka tab **Actions**. Jalankan workflow **Scan RRI every 6 hours** sekali dengan tombol **Run workflow** untuk pengujian.
6. Buka **Settings → Pages**.
7. Pada **Build and deployment**, pilih **Deploy from a branch**.
8. Branch: `main`, folder: `/ (root)`, lalu **Save**.
9. Tunggu GitHub memberikan alamat seperti `https://USERNAME.github.io/rri-reporter-monitor/`.

## Jadwal

Workflow berjalan setiap 6 jam pada UTC: 00:00, 06:00, 12:00, 18:00 UTC. Untuk WIB (UTC+7): sekitar 07:00, 13:00, 19:00, 01:00.

## Catatan

- Dashboard hanya menampilkan berita yang terdeteksi SIFA atau EDWI.
- SIFA: `(SIFA)`.
- EDWI: penulis Soufi Asegaf + `(Edwi)`, `(Edwi/Rill)`, atau `(Edwi / Rill)`.
- Tidak ada kategori SIFA + EDWI.
- Tombol Copy Link tersedia.
- Export memakai CSV yang bisa dibuka dengan Excel.
- GitHub Actions gratis memiliki batas penggunaan; jadwal 4x sehari biasanya ringan, tetapi durasi scanner bergantung pada jumlah halaman dan respons RRI.
