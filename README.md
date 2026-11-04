# binamu-content

Repo konten Instagram @binamusolusiteknologi.

- `media/` : slide carousel (JPG 1080x1350). Dipakai sebagai URL publik untuk Instagram.
- `automation/queue/` : antrian posting (JSON). Setiap file = satu post.
- `automation/run_due.py` : memposting antrian yang sudah waktunya.
- `.github/workflows/publish.yml` : jadwal Senin, Rabu, Jumat 12:00 WIB.

Kill switch: ubah variable `AUTOPOST_ENABLED` jadi `false`, atau tambahkan file `PAUSED` di root repo.

Jangan simpan token atau password di file apa pun. Gunakan Secrets di Settings > Secrets and variables > Actions.
