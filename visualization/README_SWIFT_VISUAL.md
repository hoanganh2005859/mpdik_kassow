# KR810 Swift Visualizer (Windows)

Xem robot KR810 trong Swift (roboticstoolbox-python + swift-sim), phong cách
sáng màu / xám nhạt, sàn lưới, trục XYZ rõ ràng, xoay/zoom/pan bằng chuột
trong trình duyệt.

Toàn bộ môi trường nằm trong `.venv-swift` (Python 3.11), **tách biệt hoàn
toàn** với `.venv` gốc và pipeline DLS/MuJoCo hiện tại. Không file nào dưới
`assets/kr810.urdf` bị chỉnh sửa — file phụ `assets/kr810_swift_light_gray.urdf`
được sinh ra riêng cho visualization.

## 1. File đã tạo/sửa

| File | Mô tả |
| --- | --- |
| `.venv-swift/` | Venv Python 3.11 riêng, không dùng chung với `.venv` gốc |
| `visualization/swift_smoke_test.py` | Test Panda mẫu để xác nhận Swift chạy được |
| `visualization/swift_view_kr810.py` | Viewer chính cho KR810 |
| `visualization/make_light_gray_urdf.py` | Sinh `assets/kr810_swift_light_gray.urdf` từ `assets/kr810.urdf` |
| `assets/kr810_swift_light_gray.urdf` | URDF màu xám sáng, sinh tự động (không sửa tay) |
| `.gitignore` | Thêm dòng `.venv-swift/` |
| `.venv-swift\Lib\site-packages\swift\SwiftRoute.py` | **Đã patch** — xem mục 3 |
| `.venv-swift\Lib\site-packages\swift\Swift.py` | **Đã patch** — xem mục 3 |

## 2. Setup từ đầu (CMD)

Nếu `.venv-swift` chưa tồn tại (hoặc bị xoá), tạo lại bằng CMD từ thư mục gốc repo:

```cmd
cd /d D:\data\hoang_anh\mpdik_kassow
"C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe" -m venv .venv-swift
.venv-swift\Scripts\activate.bat
python -m pip install --upgrade pip
pip install roboticstoolbox-python swift-sim
```

Bước cài ở trên sẽ kéo theo NumPy 2.x và `websockets` mới nhất, cả hai đều
**không tương thích** với `swift-sim` trên Windows — xem mục 3a và 3b để fix
(đã fix sẵn trong repo này, chỉ cần làm lại nếu tạo venv mới).

## 3. Các lỗi đã gặp và cách fix

### 3a. Lỗi NumPy 2.x (`_ARRAY_API not found` khi `import swift`)

`swift-sim` chứa extension C++ (`swift.phys`) build cho NumPy 1.x. Với NumPy
2.x sẽ báo lỗi:

```
AttributeError: _ARRAY_API not found
ImportError: numpy.core.multiarray failed to import
```

**Fix:** downgrade NumPy trong `.venv-swift` (không đụng tới `.venv` gốc):

```cmd
.venv-swift\Scripts\activate.bat
pip install "numpy<2"
```

Repo này đang dùng `numpy==1.26.4` trong `.venv-swift`.

### 3b. Lỗi `websockets` mới (`RuntimeError: no running event loop` trong `SwiftRoute.py`)

`websockets` >= 14 đổi API `websockets.serve()` sang bản asyncio mới, yêu cầu
đang chạy trong event loop. `SwiftRoute.py` của `swift-sim` dùng kiểu cũ
(`loop.run_until_complete(websockets.serve(...))`) nên bị crash ngay khi
`swift.Swift().launch()`.

**Fix:** ghim `websockets` về bản còn API cũ:

```cmd
.venv-swift\Scripts\activate.bat
pip install "websockets==12.0"
```

### 3c. Đã tự patch `SwiftRoute.py` (lỗi load mesh qua route `/retrieve/` trên Windows)

File: `.venv-swift\Lib\site-packages\swift\SwiftRoute.py`, trong
`SwiftServer.MyHttpRequestHandler.do_GET`.

**Bug 1 — lệch 1 ký tự khi cắt prefix `/retrieve/`:** code gốc
`self.path[9:]` để sót lại một dấu `/` thừa phía trước đường dẫn đã giải mã.
Trên POSIX vô hại (`//abs/path` tự rút gọn thành `/abs/path`), nhưng trên
Windows đường dẫn tuyệt đối dạng `D:\...` sẽ thành `/D:\...`, khiến
`open()` báo `OSError(22, 'Invalid argument')` — **mesh STL của KR810
(`assets/meshes/a810/*.stl`) không bao giờ load được**. Đã patch: chỉ bỏ dấu
`/` thừa khi phát hiện pattern ổ đĩa Windows (`/X:\` hoặc `/X:/`).

**Bug 2 — HTTP server đơn luồng (`socketserver.TCPServer`):** server gốc xử
lý từng kết nối một; trong lúc tab trình duyệt đang giữ kết nối, các request
`/retrieve/` để tải mesh khác bị treo/timeout. Đã patch: đổi sang
`ThreadingHTTPServer` (dùng `socketserver.ThreadingMixIn`) để mỗi request
chạy trên thread riêng.

Cả hai patch có ghi chú `# PATCHED (mpdik_kassow, Windows dev env): ...`
ngay trong file để dễ tìm lại. Nếu tạo lại `.venv-swift` từ đầu, cần patch
lại thủ công theo mô tả trên (chỉ 2 đoạn nhỏ trong `SwiftRoute.py`).

### 3d. Đã tự patch `Swift.py` (crash khi `close()` sau `launch(headless=True)`)

File: `.venv-swift\Lib\site-packages\swift\Swift.py`, hàm `_stop_threads`.
Code gốc gọi `self.server.join(1)` vô điều kiện, nhưng `self.server` chỉ
được tạo khi `headless=False`. Chạy `--headless` rồi gọi `env.close()` sẽ
crash với `AttributeError: 'Swift' object has no attribute 'server'`. Đã
patch: chỉ join khi `not self.headless`. Chỉ ảnh hưởng chế độ headless
(dùng để test nhanh không cần trình duyệt), không ảnh hưởng chế độ xem bình
thường.

### 3e. Cảnh báo vô hại lúc thoát chương trình

Khi đóng chương trình (Ctrl+C hoặc hết `--hold-seconds`), console có thể in:

```
nanobind: leaked N instances!
...
See https://nanobind.readthedocs.io/en/latest/refleaks.html
```

Đây là cảnh báo dọn bộ nhớ của binding C++ (`spatialgeometry`) lúc trình
thông dịch Python thoát — **vô hại**, không phải lỗi của visualization, có
thể bỏ qua.

## 4. Chạy smoke test (xác nhận môi trường OK)

```cmd
cd /d D:\data\hoang_anh\mpdik_kassow
.venv-swift\Scripts\activate.bat
python visualization\swift_smoke_test.py
```

Script sẽ mở tab trình duyệt, chạy animation ngắn với robot Panda mẫu, in
`SMOKE_TEST_OK`, rồi giữ tab mở tới khi bạn nhấn `Ctrl+C`.

Kiểm tra nhanh không cần trình duyệt (CI-style):

```cmd
python visualization\swift_smoke_test.py --headless
```

Tự đóng sau N giây thay vì chờ Ctrl+C:

```cmd
python visualization\swift_smoke_test.py --hold-seconds 10
```

## 5. Chạy viewer KR810

```cmd
cd /d D:\data\hoang_anh\mpdik_kassow
.venv-swift\Scripts\activate.bat
python visualization\swift_view_kr810.py
```

Script sẽ:
1. Tự sinh lại `assets/kr810_swift_light_gray.urdf` từ `assets/kr810.urdf`
   (không sửa file gốc).
2. Load KR810 (7 khớp), đặt về tư thế "ready" dễ nhìn (khuỷu tay hơi gập).
3. Mở tab trình duyệt, thêm trục XYZ tại gốc robot và tại đầu công cụ.
4. Đặt camera ở góc nhìn 3/4 mặc định.
5. Giữ tab mở tới khi bạn nhấn `Ctrl+C`.

Tuỳ chọn giống smoke test:

```cmd
python visualization\swift_view_kr810.py --headless
python visualization\swift_view_kr810.py --hold-seconds 30
```

### Chỉ sinh lại URDF màu xám sáng (không mở viewer)

```cmd
python visualization\make_light_gray_urdf.py
```

## 6. Chỉnh camera

- **Xoay (orbit):** giữ chuột trái và kéo trong cửa sổ trình duyệt.
- **Zoom:** lăn chuột (scroll wheel).
- **Pan:** giữ chuột phải (hoặc Shift + chuột trái) và kéo.

Đây là điều khiển chuột gốc của Swift (OrbitControls), không cần code gì
thêm. Muốn đặt camera mặc định khác lúc mở viewer, sửa hai hằng số trong
`visualization\swift_view_kr810.py`:

```python
CAMERA_POSITION = [2.2, -2.2, 1.6]   # vị trí camera (x, y, z), mét
CAMERA_LOOK_AT = [0.0, 0.0, 0.6]     # điểm camera nhìn vào
```

Muốn đổi tư thế robot lúc mở viewer, sửa `DEMO_Q` (7 giá trị góc khớp,
radian, phải nằm trong giới hạn khớp của `assets/kr810.urdf`).

## 7. Dừng chương trình

- Trong cửa sổ CMD đang chạy script: nhấn `Ctrl+C`.
- Đóng tab trình duyệt chỉ đóng giao diện, **không** dừng tiến trình Python —
  vẫn cần `Ctrl+C` trong CMD (hoặc dùng `--hold-seconds N` để tự thoát).

## 8. Phạm vi không đụng tới

- `.venv` gốc: không cài/gỡ gì trong đó.
- Pipeline DLS / MuJoCo (`generators/`, `evaluation*/`, `dataset_v2/`,
  `assets/kr810.xml`, ...): không đụng tới.
- `assets/kr810.urdf`: chỉ đọc, không ghi.
