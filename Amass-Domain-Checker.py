import tkinter as tk
from tkinter import messagebox, IntVar
from tkinterdnd2 import DND_FILES, TkinterDnD
import requests
import threading
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

class SubdomainChecker:
    def __init__(self, master):
        self.master = master
        master.title("AMASS DOMAIN CHECKER")
        master.geometry("1100x900")

        self.label = tk.Label(master, text="Amass çıktısını yüklemek için dosyayı sürükleyin:")
        self.label.pack(pady=10)

        self.textbox = tk.Text(master, height=30, width=100, font=("Arial", 12))
        self.textbox.pack(pady=10)

        self.result_count_label = tk.Label(master, text="Çalışan Domainler: 0", font=("Arial", 12))
        self.result_count_label.pack(pady=5)

        self.redirect_var = IntVar()
        self.redirect_checkbox = tk.Checkbutton(master, text="Yönlendirmeli (301) olan domainleride kayıt et ", fg="purple" ,font=("Arial", 12 ), variable=self.redirect_var, command=self.update_redirect_message)
        self.redirect_checkbox.pack(pady=5)

        self.redirect_message = tk.Label(master, text="Yönlendirmeli domainler kayıt edilmeyecek", fg="red", font=("Arial", 10))
        self.redirect_message.pack(pady=5)

        self.redirect_note = tk.Label(master, text="", font=("Arial", 10), fg="red")
        self.redirect_note.pack(pady=5)

        self.check_button = tk.Button(master, text="Kontrol Et", command=self.start_check, bg="blue", fg="white")
        self.check_button.pack(pady=5)

        self.output_button = tk.Button(master, text="Çıktıyı Kaydet", command=self.save_output, bg="Black", fg="white")
        self.output_button.pack(pady=5)

        self.results = set()
        self.redirect_results = set()
        self.exclude_keywords = ["cloudflare", "azure", "cdn", "netblock", "cname", "amazonaws", "awsdns"]

        self.textbox.drop_target_register(DND_FILES)
        self.textbox.dnd_bind('<<Drop>>', self.on_drop)

        self.textbox.tag_config("green", foreground="green")
        self.textbox.tag_config("red", foreground="red")
        self.textbox.tag_config("blue", foreground="blue")
        self.textbox.tag_config("signature", foreground="blue", font=("Arial", 10, "italic"))

        self.signature_label = tk.Label(master, text="BU ARAÇ MAJESTAR TARAFINDAN OLUŞTURULMUŞTUR", font=("Arial", 10, "italic"), fg="blue")
        self.signature_label.pack(pady=5)

        self.url_count = 0

    def update_redirect_message(self):
        if self.redirect_var.get() == 1:
            self.redirect_message.config(text="Yönlendirmeli domain bulunursa kayıt edilecektir", fg="green")
        else:
            self.redirect_message.config(text="Yönlendirmeli domainler kayıt edilmeyecektir", fg="red")
            self.redirect_note.config(text="")

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
        self.results.clear()
        self.redirect_results.clear()
        self.url_count = 0
        self.result_count_label.config(text="Çalışan Domainler: 0")
        self.label.config(text="İşlem Başladı Lütfen Bekleyin", fg="red")

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
        with ThreadPoolExecutor(max_workers=50) as executor:
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

        try:
            response = requests.get(https_url, timeout=10)
            if response.status_code in (200, 301):
                if response.status_code == 200 and https_url not in self.results:
                    self.results.add(https_url)
                    self.url_count += 1
                    self.master.after(0, self.display_result, https_url, "200 OK", "green")
                    self.master.after(0, self.update_count)
                elif self.redirect_var.get() == 1 and response.status_code == 301 and https_url not in self.redirect_results:
                    self.redirect_results.add(https_url)
                    self.master.after(0, self.display_result, https_url, "301 Moved Permanently", "blue")
                return
        except requests.RequestException:
            self.master.after(0, self.display_result, https_url, "Hata", "red")

        try:
            response = requests.get(http_url, timeout=10)
            if response.status_code in (200, 301):
                if response.status_code == 200 and http_url not in self.results:
                    self.results.add(http_url)
                    self.url_count += 1
                    self.master.after(0, self.display_result, http_url, "200 OK", "green")
                    self.master.after(0, self.update_count)
                elif self.redirect_var.get() == 1 and response.status_code == 301 and http_url not in self.redirect_results:
                    self.redirect_results.add(http_url)
                    self.master.after(0, self.display_result, http_url, "301 Moved Permanently", "blue")
        except requests.RequestException:
            self.master.after(0, self.display_result, http_url, "Hata", "red")

    def display_result(self, url, status, color):
        self.textbox.insert(tk.END, f"{url} - - > ")
        if color == "green":
            self.textbox.insert(tk.END, status + "\n", "green")
        elif color == "blue":
            self.textbox.insert(tk.END, status + "\n", "blue")
        else:
            self.textbox.insert(tk.END, status + "\n", "red")
        self.textbox.see(tk.END)

    def update_count(self):
        self.result_count_label.config(text=f"Çalışan Domainler: {self.url_count}")

    def final_message(self):
        self.textbox.insert(tk.END, "\nTüm işlemler bitti, çıktı kaydedildi.\n")
        self.save_output()
        self.label.config(text="Amass çıktısını yüklemek için dosyayı sürükleyin:", fg="black")

    def save_output(self):
        if not self.results and not self.redirect_results:
            return

        with open("output.txt", "w") as f:
            for result in self.results:
                f.write(f"{result}\n")
            if self.redirect_var.get() == 1:
                for redirect in self.redirect_results:
                    f.write(f"{redirect}\n")
        if self.master.winfo_exists():
            messagebox.showinfo("Başarılı", "Çıktı 'output.txt' dosyasına kaydedildi.")

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = SubdomainChecker(root)
    root.mainloop()
