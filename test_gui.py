import customtkinter as ctk

try:
    # --- Configuración de la Apariencia ---
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    # --- Creación de la Ventana ---
    app = ctk.CTk()
    app.title("Prueba de GUI")
    app.geometry("400x200")

    # --- Creación de un Widget Simple (Etiqueta) ---
    label = ctk.CTkLabel(app, text="Si puedes leer esto, ¡la librería funciona!", font=ctk.CTkFont(size=18))
    label.pack(pady=40, padx=20) # .pack() es una forma simple de poner algo en la ventana

    # --- Iniciar la App ---
    app.mainloop()

except Exception as e:
    print("Ocurrió un error al crear la GUI:")
    print(e)

