# Báo Cáo Thực Hành Lab 25 — GPU FinOps Optimization

**Học viên:** Trương Đình Khoa  
**Mã học viên:** 2A202601297  
**Email thông báo khi hoàn thành:** `dinkhoa288@gmail.com`  
**Khóa học:** AICB · Phase 2 · Track 2 (Infrastructure) · Day 25  
**Ngày thực hiện:** 27/08/2026  

---

## 1. Tóm Tắt Kết Quả (Executive Summary)

Với vai trò FinOps Engineer tại **NimbusAI**, bài thực hành này đã tiến hành kiểm toán toàn diện hạ tầng GPU, phân bổ chi phí và áp dụng các đòn bẩy FinOps tối ưu chi phí phục vụ LLM:

* **Tổng chi phí hàng tháng:** Từ **$27,133** (Baseline) giảm xuống **$14,626** (Optimized), đạt mức **tiết kiệm $12,507/tháng (46%)**.
* **Đơn vị kinh tế (Unit Economics):** Giá trung bình **`$/1M-token`** giảm từ **$6.488** xuống **$1.126** (giảm **82.6%**).
* **Kết quả Kiểm tra Tự động (`verify.py`):** Đạt **11/11 checks PASS**.
* **Kết quả Unit Tests (`pytest`):** Đạt **16/16 tests PASS**.
* **Phần mở rộng ("Your Turn"):** Hoàn thành **toàn bộ 5/5 Extensions**.

---

## 2. Phân Tích Chi Tiết Chi Phí (Baseline vs. Optimized)

### 2.1 Bảng Phân Bổ Chi Phí Tiết Kiệm Theo Đòn Bẩy (FinOps Levers)

| Đòn bẩy tối ưu (FinOps Lever) | Chi phí tiết kiệm (USD/tháng) | Tỷ trọng tiết kiệm (%) |
|---|---|---|
| **Purchasing Strategy (Spot / Reserved)** | $10,040 | 80.3% |
| **Inference Optimization (Cascade / Cache / Batch)** | $1,212 | 9.7% |
| **Right-size Util-lies (Downgrade over-provisioned GPUs)** | $655 | 5.2% |
| **Kill Idle GPUs (Tắt GPU bỏ trống)** | $600 | 4.8% |
| **TỔNG CỘNG** | **$12,507** | **100.0%** |

---

## 3. Phân Tích Kỹ Thuật 5 Missions

### Mission 1 — Kiểm Toán Hiệu Quả GPU & "GPU-Util Lie"
* **Phát hiện GPU-Util Lie:** `nvidia-smi` đo thời lượng clock hoạt động chứ không đo lượng FLOPs thực sự. `gpu-h100-4` đạt **98.2% GPU-Util** nhưng chỉ đạt **MFU 0.194 (19.4%)**, cho thấy GPU bị nghẽn bộ nhớ (memory stall / I/O wait) nghiêm trọng.
* **Lãng phí Idle:** Phát hiện 8 giờ GPU bỏ trống trên `gpu-h100-5`, gây lãng phí **$20.00/ngày ($600/tháng)**.

### Mission 2 — Đòn Bẩy Chi Phí Inference
* **Kết hợp 3 đòn bẩy:** 
  1. **Cascade:** Chuyển các request đơn giản từ model lớn sang model nhỏ (giảm giá 15×).
  2. **Prompt Caching:** Chiết khấu 90% cho phần input token đã cache (`cache_discount = 0.10`).
  3. **Batch API:** Chiết khấu 50% cho request không cần xử lý thời gian thực (`batch_discount = 0.50`).
* **Stack Chiết Khấu (Discount Stack):** Khi gộp Batch + 100% Cache hit, chi phí input giảm còn `0.50 × 0.10 = 0.05` (tiết kiệm **95%**).

### Mission 3 — Chiến Lược Mua GPU (Purchasing Strategy)
* **Điểm hòa vốn (Break-even utilization):** Với mức chiết khấu Reserved 3 năm 45%, mức sử dụng hòa vốn là `1 - 0.45 = 55%` (tương đương 13.2 giờ/ngày).
* **Đề xuất mua:** 
  * Các job huấn luyện (`job-train-llm`, `job-train-embed`, `job-finetune`) có tính năng checkpoint được chuyển sang **Spot Instance** (giảm chi phí từ $12,000 xuống $7,596/tháng).
  * Các job inference có duty cycle cao (`job-infer-chat`, `job-infer-rag`, `job-infer-search`) chuyển sang **Reserved Instance** 3-năm.
* **Kết quả:** Giảm chi phí mua GPU từ $25,667 xuống $15,627/tháng (**tiết kiệm 39.1%**).

### Mission 4 — Phân Bổ Chi Phí (Cost Allocation) & chuẩn FOCUS
* **Tag Coverage:** Đạt **92%**, vượt ngưỡng yêu cầu 80% để mở cổng **Chargeback**.
* **Đã xuất file chuẩn FOCUS:** `outputs/focus_export.csv` gồm 50 bản ghi chuẩn mở FinOps Foundation với đầy đủ thông tin `BillingAccountId`, `ChargePeriodStart`, `BilledCost`, `team`, `project`.

### Mission 5 — Báo Cáo Tổng Hợp & Bền Vững (Sustainability)
* Đã tạo tự động báo cáo `outputs/report.md` chứa số liệu tổng hợp.
* Chỉ số bền vững: **0.24 Wh/query**, phát thải **0.091 gCO2e/query**, vùng hạ tầng tối ưu nhất về năng lượng và carbon là **`europe-north1`** (Na Uy).

---

## 4. Kết Quả 5 Phần Mở Rộng ("Your Turn" Extensions)

Đã triển khai và đo lường trực tiếp trong file `missions/extension_analysis.py`:

1. **Extension 1 (Cải thiện `recommend_tier`):** Tích hợp yếu tố rủi ro gián đoạn theo loại GPU và thời lượng công việc (`job_days`). Tránh cam kết Reserved dài hạn cho các dự án ngắn hạn (< 30 ngày).
2. **Extension 2 (Right-sizing theo MBU & $/GB-VRAM):** Phân tích 5 GPU bị nghẽn băng thông memory-bound. Đề xuất hạ cấp từ H100 (80GB VRAM, $2.5/h) xuống A100 (80GB VRAM, $1.79/h) cho giai đoạn decode, tiết kiệm $511.20/tháng/GPU.
3. **Extension 3 (Kinh tế học Caching - `cache_is_worth_it`):** Triển khai hàm kiểm tra điểm hòa vốn. Với số lần đọc lại trung bình `avg_reads = 2.5` và chi phí ghi $3.0/1M, việc caching mang lại lợi ích tài chính thực sự (`cache_is_worth_it = True`).
4. **Extension 4 (Ngân sách & Tiêu thụ Năng lượng cho Reasoning):** Phân tích các request `is_reasoning=1`. Dù số lượng nhỏ, traffic reasoning tiêu thụ **94.0% tổng năng lượng** (do hệ số nhân năng lượng ~80×). Đề xuất đặt hạn ngạch (quota) và routing rule cho reasoning traffic.
5. **Extension 5 (Lịch trình nhận thức Carbon - Carbon-Aware Scheduling):** Chuyển toàn bộ các job huấn luyện có thể gián đoạn từ vùng `us-east-1` (380 gCO2/kWh) sang vùng `europe-north1` (30 gCO2/kWh), giúp **giảm 1,479.5 kgCO2/tháng (giảm 92.1% phát thải carbon)**.

---

## 5. Khuyến Nghị Hành Động Cho NimbusAI

1. **Hành động 1 (Ưu tiên cao nhất - Quick Win):** Tắt toàn bộ GPU idle và chuyển các công việc huấn luyện sang Spot Instance kèm checkpointing tự động.
2. **Hành động 2:** Triển khai Gateway Inference bắt buộc áp dụng Model Cascade, Prompt Caching và Batch API.
3. **Hành động 3:** Thực hiện Chargeback chính thức cho các đội nhóm (dựa trên 92% tag coverage) để nâng cao nhận thức sử dụng tài nguyên.
4. **Hành động 4:** Áp dụng Carbon-aware Scheduling cho các job batch/training sang vùng `europe-north1`.

---

## 6. Thông Báo Hoàn Thành Qua Email
* Theo quy định bài học, thông báo hoàn thành bài lab đã được ghi nhận để gởi tới email: **`dinkhoa288@gmail.com`**.
