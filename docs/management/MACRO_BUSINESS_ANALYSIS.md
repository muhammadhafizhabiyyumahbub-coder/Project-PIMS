# Analisis Bisnis Macro Engine PIMS

**Penyusun: Damar subagent**

## Ringkasan eksekutif — lima series untuk investor

1. **CPI (CPIAUCSL):** perubahan CPI year-on-year (YoY) menunjukkan inflasi; percepatan inflasi dapat mengikis daya beli dan menekan valuasi aset berjangka panjang.
2. **GDP (GDPC1):** pertumbuhan GDP riil YoY memberi indikasi arah aktivitas ekonomi; pertumbuhan menguat umumnya mendukung pendapatan perusahaan, sedangkan pelemahan meningkatkan risiko laba.
3. **UNRATE:** tingkat pengangguran menggambarkan kondisi pasar tenaga kerja; kenaikan berkelanjutan dapat menandakan pelemahan permintaan dan tekanan terhadap pendapatan.
4. **FEDFUNDS:** suku bunga kebijakan efektif AS menggambarkan stance moneter; suku bunga tinggi menaikkan biaya pendanaan dan tingkat diskonto, sementara penurunan dapat melonggarkan kondisi keuangan.
5. **10YUSTR (FRED DGS10):** yield Treasury AS 10 tahun mencerminkan biaya pinjaman jangka panjang dan ekspektasi pasar; yield naik dapat menekan harga obligasi lama dan valuasi saham sensitif suku bunga.

## Interpretasi bisnis metrik

| Series / metrik | Makna untuk investor | Catatan interpretasi |
|---|---|---|
| CPI YoY | Inflasi konsumen tahunan; input untuk menilai daya beli, biaya, dan tekanan suku bunga. | Rumus perubahan relatif: `(CPI_t - CPI_t-12) / CPI_t-12`; nyatakan hasil sebagai persen. CPI bukan inflasi inti. |
| GDP YoY | Pertumbuhan output riil tahunan; konteks untuk prospek permintaan dan pendapatan korporasi. | GDPC1 berfrekuensi kuartalan, sehingga perbandingan YoY lazimnya membandingkan kuartal dengan kuartal yang sama tahun sebelumnya (lag empat kuartal), bukan lag 12 observasi. |
| UNRATE | Persentase angkatan kerja yang menganggur; kenaikan dapat mengisyaratkan pendinginan pasar tenaga kerja. | Nilai level adalah persen. Perubahan YoY sebaiknya dibedakan dari perubahan poin persentase; kenaikan UNRATE bukan sinyal ekspansi. |
| FEDFUNDS | Tingkat federal funds efektif; proksi kondisi moneter jangka pendek AS. | Level dinyatakan persen. Perubahan suku bunga dalam poin persentase lebih mudah ditafsirkan daripada persentase perubahan relatif. |
| 10YUSTR / DGS10 | Yield Treasury AS 10 tahun; acuan suku bunga jangka panjang, biaya modal, dan diskonto. | FRED series DGS10 bersifat harian dan bernama “Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity”; bukan yield obligasi korporasi. Pilih aturan agregasi untuk menyelaraskan frekuensi. |
| Rolling average 12 periode | Menghaluskan volatilitas jangka pendek dan membantu melihat arah tren. | “12 periode” berarti 12 observasi, bukan selalu 12 bulan: GDP kuartalan = 12 kuartal; DGS10 harian = 12 hari kecuali diagregasi lebih dulu. |
| Z-score | Menunjukkan jarak observasi dari rata-rata historis dalam satuan simpangan baku. | Z-score positif berarti di atas rata-rata historis, bukan otomatis baik; interpretasi bergantung indikator (mis. pengangguran tinggi dapat buruk). Sebutkan jendela historis dan penanganan revisi. |

## Regime dan implikasi portofolio

Menurut spesifikasi data saat ini, regime ditetapkan **expansion bila Z > 0, contraction bila Z ≤ 0**. Ini adalah aturan klasifikasi sederhana terhadap seri/indikator yang distandardisasi, bukan siklus bisnis resmi atau rekomendasi investasi. Bila diterapkan per-series, hasil dapat berbeda antarindikator; bila digabung, bobot, normalisasi, dan aturan agregasi perlu ditetapkan terlebih dahulu. Z-score positif untuk inflasi atau pengangguran tidak bermakna “ekonomi ekspansi”.

| Regime | Pembacaan bisnis | Contoh keputusan untuk dipertimbangkan (bukan rekomendasi personal) |
|---|---|---|
| Expansion | Aktivitas/pertumbuhan menguat menurut indikator yang dipilih. Prospek pendapatan dapat membaik, tetapi inflasi dan yield tetap perlu dipantau. | Investor dapat meninjau eksposur ke saham siklikal atau kredit berkualitas; tetap uji sensitivitas valuasi terhadap yield dan hindari menaikkan risiko hanya karena label regime. |
| Contraction | Aktivitas melemah atau indikator berada di bawah baseline; risiko penurunan laba dan volatilitas dapat meningkat. | Investor dapat meninjau likuiditas, diversifikasi, kualitas neraca, dan durasi obligasi sesuai toleransi risiko; lakukan stress test dan hindari menganggap obligasi selalu naik saat contraction. |

### Cara membaca kombinasi indikator

- **GDP melambat + UNRATE naik:** risiko pelemahan permintaan dan laba meningkat; cek konfirmasi lintas rilis, karena data tertinggal.
- **CPI tetap tinggi + FEDFUNDS naik:** kondisi moneter lebih ketat dapat menekan aset berdurasi panjang; bandingkan inflasi dengan yield nominal secara hati-hati.
- **10Y yield naik:** dapat mencerminkan ekspektasi pertumbuhan/inflasi lebih tinggi atau premi term lebih besar; arah yield saja tidak menentukan regime.

## Batasan dan penggunaan

FRED series berpusat pada ekonomi AS; jangan menganggapnya mewakili Indonesia atau aset IDR/IDX tanpa validasi. Data makro dirilis dengan jeda dan dapat direvisi. Kesimpulan regime karenanya bersifat kontekstual, bukan prediksi atau sinyal transaksi. Spesifikasi saat ini mencantumkan YoY change dengan lag 12 untuk semua seri, tetapi hal itu tidak cocok langsung untuk GDP kuartalan dan metrik perubahan rate/yield; samakan definisi lag, frekuensi, dan unit sebelum penggunaan produksi. Keputusan alokasi perlu mempertimbangkan tujuan, horizon, biaya, pajak, serta toleransi risiko investor.
