# DSP Plotter Demo

Mục tiêu của dự án là minh họa các khái niệm xử lý tín hiệu số (DSP) bằng Python. Repo này tạo tín hiệu mẫu, thiết kế bộ lọc FIR/IIR và hiển thị kết quả bằng đồ thị để dễ quan sát.

## Mục lục

- [Tính năng](#tính-năng)
- [Yêu cầu](#yêu-cầu)
- [Cài đặt](#cài-đặt)
- [Cách sử dụng nhanh](#cách-sử-dụng-nhanh)
- [Ảnh minh họa](#ảnh-minh-họa)
- [Cửa sổ FIR được so sánh](#cửa-sổ-fir-được-so-sánh)
- [Cấu trúc dự án](#cấu-trúc-dự-án)
- [Ghi chú](#ghi-chú)

## Tính năng

- So sánh FIR và IIR cơ bản trên cùng một tín hiệu nhiễu.
- So sánh 4 kiểu cửa sổ FIR: Chữ nhật, Hamming, Hanning (hann), Blackman.
- Vẽ tín hiệu trong miền thời gian và đáp ứng tần số theo dB.
- Tổ chức mã theo từng file nhỏ, dễ sửa và dễ mở rộng.

## Yêu cầu

- Python 3.10 trở lên
- `numpy`
- `scipy`
- `matplotlib`

## Cài đặt

Tạo và kích hoạt môi trường ảo nếu cần, sau đó cài phụ thuộc:

```bash
python -m pip install numpy scipy matplotlib
```

## Cách sử dụng nhanh

### FIR và IIR cơ bản

```bash
python plotter.py
```

Kết quả hiển thị 2 bảng:

- Bảng 1: FIR và IIR cơ bản trên tín hiệu nhiễu 5 Hz + 150 Hz
- Bảng 2: tín hiệu sau lọc theo cấu trúc hiện tại của chương trình

### So sánh 4 cửa sổ FIR

```bash
python plotter_window.py
```

Kết quả hiển thị 3 bảng:

- Bảng 1: hệ số bộ lọc `h[n]` của 4 cửa sổ
- Bảng 2: đáp ứng tần số `|H(f)|` theo dB
- Bảng 3: tín hiệu sau lọc theo thời gian

## Ảnh minh họa

Nếu bạn muốn thêm screenshot vào README trên GitHub, hãy làm như sau:

1. Tạo một thư mục, ví dụ `assets/` hoặc `images/` trong repo.
2. Lưu file ảnh vào đó, ví dụ `assets/plotter.png` hoặc `assets/window-comparison.png`.
3. Chèn ảnh bằng Markdown theo cú pháp sau:

```markdown
![Mô tả ảnh](assets/plotter.png)
```

Bạn cũng có thể ghi chú ngay bên dưới ảnh để giải thích nội dung.

Ví dụ:

```markdown
## Screenshot

### Plotter FIR và IIR

![Plotter FIR và IIR](assets/plotter.png)

### So sánh cửa sổ FIR

![So sánh cửa sổ FIR](assets/window-comparison.png)
```

## Cửa sổ FIR được so sánh

- **Chữ nhật**: đơn giản, nhưng thường có gợn phụ lớn hơn.
- **Hamming**: giảm gợn phụ tốt hơn cửa sổ chữ nhật.
- **Hanning (hann)**: cân bằng giữa độ mượt và khả năng triệt nhiễu.
- **Blackman**: suy hao dải chặn tốt hơn, nhưng vùng chuyển tiếp rộng hơn.

Lưu ý: trong SciPy, tham số cửa sổ dùng tên `hann`.

## Cấu trúc dự án

```text
FIR.py
IIR.py
IIR_2side.py
plotter.py
plotter_window.py
signal_gen.py
README.md
```

## Ghi chú

- Các đồ thị dùng tín hiệu mẫu sinh tự động, không cần file dữ liệu ngoài.
- Tham số lọc chính như `numtaps`, `cutoff`, `fs` được đặt trực tiếp trong code.
- Đây là dự án mang tính học tập, phù hợp để tìm hiểu FIR, IIR và tác động của các kiểu cửa sổ lên bộ lọc số.
