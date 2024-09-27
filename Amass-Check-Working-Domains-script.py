import tkinter as tk
from tkinter import messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import requests
import threading
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

class SubdomainChecker:
    def __init__(self, master):
        self.master = master
        master.title("Subdomain Checker")

        self.label = tk.Label(master, text="Amass çıktısını yüklemek için dosyayı sürükleyin:")
        self.label.pack(pady=10)

        self.textbox = tk.Text(master, height=40, width=120, font=("Arial", 12))
        self.textbox.pack(pady=10)

        self.check_button = tk.Button(master, text="Kontrol Et", command=self.start_check)
        self.check_button.pack(pady=5)

        self.output_button = tk.Button(master, text="Çıktıyı Kaydet", command=self.save_output)
        self.output_button.pack(pady=5)

        self.results = []
        self.exclude_keywords = ["cloudflare", "azure", "cdn", "netblock", "cname", "amazonaws", "awsdns"]

        # Sürükleyip bırakma desteği
        self.textbox.drop_target_register(DND_FILES)
        self.textbox.dnd_bind('<<Drop>>', self.on_drop)

        # Renk tanımlamaları
        self.textbox.tag_config("green", foreground="green")
        self.textbox.tag_config("red", foreground="red")

    def on_drop(self, event):
        file_path = event.data.strip('{}')
        self.load_file(file_path)

    def load_file(self, file_path):
        try:
            with open(file_path, 'r') as file:
                input_text = file.read()
                self.textbox.delete(1.0, tk.END)
                self.textbox.insert(tk.END, input_text)
        except Exception as e:
            messagebox.showerror("Hata", f"Dosya yüklenirken hata oluştu: {str(e)}")

    def start_check(self):
        self.results = []
        input_text = self.textbox.get(1.0, tk.END).strip()

        if not input_text:
            messagebox.showwarning("Uyarı", "Lütfen önce bir dosya yükleyin.")
            return

        domains = set(re.findall(r'(\b[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}\b)', input_text))
        filtered_domains = [domain for domain in domains if not any(keyword in domain for keyword in self.exclude_keywords)]

        if not filtered_domains:
            messagebox.showwarning("Uyarı", "Geçerli bir alan adı bulunamadı.")
            return

        self.textbox.delete(1.0, tk.END)
        threading.Thread(target=self.check_subdomains, args=(filtered_domains,)).start()

    def check_subdomains(self, domains):
        with ThreadPoolExecutor(max_workers=50) as executor:  # 50 eş zamanlı iş
            futures = {executor.submit(self.check_url, domain): domain for domain in domains}
            for future in as_completed(futures):
                domain = futures[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"Hata: {e}")

        self.master.after(0, self.final_message)

    def check_url(self, domain):
        https_url = f"https://{domain}"
        http_url = f"http://{domain}"

        # İlk önce HTTPS kontrolü
        try:
            response = requests.get(https_url, timeout=5)  # 5 saniye bekle
            if response.status_code in (200, 301):
                self.results.append(https_url)
                self.master.after(0, self.display_result, https_url, f"{response.status_code} OK", "green")
                return  # HTTP kontrolüne geçme
        except requests.RequestException:
            self.master.after(0, self.display_result, https_url, "Hata", "red")

        # HTTPS başarısızsa HTTP kontrolü
        try:
            response = requests.get(http_url, timeout=5)  # 5 saniye bekle
            if response.status_code in (200, 301):
                self.results.append(http_url)
                self.master.after(0, self.display_result, http_url, f"{response.status_code} OK", "green")
        except requests.RequestException:
            self.master.after(0, self.display_result, http_url, "Hata", "red")

    def display_result(self, url, status, color):
        self.textbox.insert(tk.END, f"{url} --> {status}\n")
        self.textbox.tag_add(color, f"{tk.END}-1c linestart", tk.END)
        self.textbox.see(tk.END)

    def final_message(self):
        self.textbox.insert(tk.END, "\nTüm işlemler bitti, çıktı kaydedildi.\n")
        self.save_output()

    def save_output(self):
        if not self.results:
            return

        with open("output.txt", "w") as f:
            for result in self.results:
                f.write(f"{result}\n")
        if self.master.winfo_exists():
            messagebox.showinfo("Başarılı", "Çıktı 'output.txt' dosyasına kaydedildi.")

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = SubdomainChecker(root)
    root.mainloop()
