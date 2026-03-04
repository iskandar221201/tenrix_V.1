# Panduan Uji Coba Manual End-to-End Tenrix AI Pipeline

Dokumen ini berisi panduan tahap demi tahap untuk melakukan pengujian manual pada 6 fitur terbaru Tenrix AI Pipeline, menggunakan dataset `war_economic_impact_dataset.csv`.

## Persiapan
1. Pastikan Anda berada di direktori proyek Tenrix.
2. Jalankan aplikasi melalui terminal:
   ```bash
   python main.py
   ```

## Tahap 1: Memuat Data (Load Data)
1. Di menu utama, tekan **`[L]`** untuk Load Data.
2. Masukkan lokasi file dataset: `intruction/war_economic_impact_dataset.csv`
3. Tunggu hingga profil data selesai dihitung (Profiler).
4. Kembali ke menu utama.

## Tahap 2: Menguji Fitur Analisis dan AI
Dari menu utama, tekan **`[A]`** (Ask AI). Kita akan memberikan beberapa pertanyaan beruntun untuk menguji Guardrails, AI Interpreter (Counter-Intuitive/Wild Logic), Confidence Score, Session Memory, dan Interactive Refinement.

### Pertanyaan 1 (Menguji Counter-Intuitive, Guardrails, & Confidence)
Ketik pertanyaan berikut:
> "Apakah ada hubungan antara jatuhnya GDP (GDP_Change_%) dengan tingkat Inflasi (Inflation_Rate_%)? Buatkan analisis statistiknya."

**Apa yang harus diperhatikan pada hasil ini:**
- **[FITUR 1] Guardrails:** Perhatikan apakah muncul peringatan pelanggaran asumsi (misalnya `[WARNING] 1 asumsi statistik tidak terpenuhi: shapiro_wilk`). Data historis riil seringkali tidak berdistribusi normal, sehingga peringatan pasti muncul jika planner memilih korelasi atau regresi linier.
- **[FITUR 4] Confidence Score:** Di atas visualisasi, Anda harusnya melihat Confidence Bar (misalnya `[=====     ] 50%`) dan list alasan pinalti (misalnya karena asumsi statistik gagal atau model fit yang buruk).
- **[FITUR 2] Wild Logic / Counter-Intuitive:** Di bawah analisis standar, AI seharusnya bisa mengeluarkan opini "Insight di luar nalar" tentang data inflasi dan GDP tersebut.

### Tahap 3: Follow-Up & Refinement (Menguji Session Memory & Interactive Refinement)
Setelah hasil pertama selesai diprint, aplikasi akan menampilkan menu *Interactive Refinement* (tanya otomatis).

**Pilih salah satu nomor referensi atau ketik *custom*:**
Kamu bisa langsung menggunakan salah satu angka yang disarankan (misalnya `[1]`, `[2]`, atau `[3]`), ATAU ketik pertanyaan custom di bawah ini untuk menguji memori sesi.
> "Dari negara-negara di analisis kita sebelumnya, sektor apa (Most_Affected_Sector) yang paling menderita saat pengangguran melonjak tajam (Unemployment_Spike_Percentage_Points)?"

**Apa yang harus diperhatikan pada hasil ini:**
- **[FITUR 6] Interactive Refinement:** Menu pilihan tersebut sukses mempercepat work-flow.
- **[FITUR 3] Session Memory:** AI planner akan memutuskan jenis analisis tanpa meminta data ulang terkait dengan tren sebelumnya (konteks akan dijaga selama Anda belum keluar dari aplikasi/menu analyzer).

## Tahap 4: Menguji Ekspor Report
1. Ketik `/exit` atau `B` untuk kembali ke Menu Utama.
2. Tekan **`[E]`** (Export report).
3. Pilih output PDF & Excel, kemudian setujui pembuatan laporan.
4. Tunggu beberapa detik hingga file terbentuk.

Buka file PDF dan Excel yang baru saja digenerate (`/exports` folder) dan perhatikan:
- **[FITUR 5] Executive Summary:** Pastikan ada rangkuman holistik/paragraf konklusi yang merangkum gabungan dari Pertanyaan 1 dan Pertanyaan 2 di bagian paling atas laporan PDF, dan di sheet `[README]` pada file Excel.
- **[Ekstra FITUR 1] Visualisasi Guardrails:** 
  - Pada **PDF**: Pastikan ada kotak peringatan Guardrail merah/kuning muda pada analisis yang tidak memenuhi standar statistik.
  - Pada **Excel**: Pastikan ada **Sheet khusus "Data Quality"** yang melampirkan list pelanggaran asumsi sebelum analisis dimulai.

---
**Ceklist Keberhasilan Fitur:**
- [ ] Fitur 1: Guardrails memunculkan Warning Asumsi.
- [ ] Fitur 2: Insight "Wild Logic" (Counter-Intuitive) muncul.
- [ ] Fitur 3: Tidak ada pengulangan prompt AI berulang, karena memori sesi terjaga secara lokal.
- [ ] Fitur 4: Angka dan Bar 'Confidence Score' rilis tanpa error.
- [ ] Fitur 5: Lembar hasil ekspor menyertakan Executive Summary bahasa Inggris/Indonesia.
- [ ] Fitur 6: Prompt Rekomendasi di terminal muncul pasca eksekusi hasil.
