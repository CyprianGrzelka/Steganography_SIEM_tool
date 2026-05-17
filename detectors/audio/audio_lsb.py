import wave
import struct
import math

def text_to_bits(text):
    return ''.join(f'{byte:08b}' for byte in text.encode('utf-8'))

def bits_to_text(bits):
    bytes_list = [int(bits[i:i+8], 2) for i in range(0, len(bits), 8)]
    return bytes(bytes_list).decode('utf-8')

def hide_message(input_audio, message, output_audio, group_size=8):
    # Open WAV
    with wave.open(input_audio, 'rb') as audio:
        params = audio.getparams()
        n_channels, sampwidth, framerate, n_frames = params[:4]
        frames = audio.readframes(n_frames)
    
    # Convert frames to samples
    sample_count = n_frames * n_channels
    format_char = {1: 'B', 2: 'h'}[sampwidth]  # 8-bit unsigned or 16-bit signed
    samples = list(struct.unpack(f"<{sample_count}{format_char}", frames))

    # Prepare message
    message_bits = text_to_bits(message)
    message_length = len(message_bits)
    length_bits = f'{message_length:032b}'  # 32 bits to encode length
    full_bits = length_bits + message_bits

    total_groups_needed = len(full_bits)
    total_groups_available = len(samples) // group_size

    if total_groups_needed > total_groups_available:
        raise ValueError(f"Za mało danych audio, by ukryć wiadomość!\n"
                         f"Potrzeba {total_groups_needed * group_size} próbek, dostępne: {len(samples)}"
                        )

    # Modify LSB of samples in each group to match bit parity
    for i, bit in enumerate(full_bits):
        group = samples[i * group_size:(i + 1) * group_size]
        parity = sum(s & 1 for s in group) % 2
        target_parity = int(bit)

        if parity != target_parity:
            # Flip LSB of first sample to change parity
            group[0] ^= 1
        samples[i * group_size:(i + 1) * group_size] = group

    # Pack samples back
    modified_frames = struct.pack(f"<{len(samples)}{format_char}", *samples)

    # Save to output
    with wave.open(output_audio, 'wb') as output:
        output.setparams(params)
        output.writeframes(modified_frames)

    print(f"[✓] Wiadomość ukryta w {output_audio}")

def extract_message(stego_audio, group_size=8):
    with wave.open(stego_audio, 'rb') as audio:
        params = audio.getparams()
        n_channels, sampwidth, framerate, n_frames = params[:4]
        frames = audio.readframes(n_frames)

    sample_count = n_frames * n_channels
    format_char = {1: 'B', 2: 'h'}[sampwidth]
    samples = list(struct.unpack(f"<{sample_count}{format_char}", frames))

    total_groups_available = len(samples) // group_size

    # Odczytaj 32 bity długości wiadomości
    length_bits = ''
    for i in range(32):
        group = samples[i * group_size:(i + 1) * group_size]
        parity = sum(s & 1 for s in group) % 2
        length_bits += str(parity)

    message_length = int(length_bits, 2)

    # Sprawdź, czy ukryto wiadomość
    if message_length == 0 or (32 + message_length) > total_groups_available:
        print("[!] Nie znaleziono ukrytej wiadomości lub długość jest nieprawidłowa.")
        return ""

    # Odczytaj wiadomość
    message_bits = ''
    for i in range(32, 32 + message_length):
        group = samples[i * group_size:(i + 1) * group_size]
        parity = sum(s & 1 for s in group) % 2
        message_bits += str(parity)

    try:
        return bits_to_text(message_bits)
    except Exception as e:
        print(f"[!] Błąd dekodowania wiadomości: {e}")
        return ""

hide_message("input_10.wav", "Hello World!", "output_stego.wav")
msg = extract_message("output_stego.wav")
print("Odczytana wiadomość z pliku 10sek:", msg)

hide_message("input_30.wav", """Jak korzystać z Generatora Losowych Słów?
Wybór typu słów: Korzystanie z naszego Generatora Losowych Słów jest niezwykle proste i intuicyjne. Po pierwsze, musisz zdecydować, jaki rodzaj słów chcesz wygenerować. Możesz wybrać z trzech głównych kategorii: rzeczowniki, czasowniki, i przymiotniki. Każda z tych kategorii pomoże Ci dopasować słowa do specyficznych potrzeb – czy to pisania kreatywnego, nauki języka, czy organizacji gier.
Ustawienia dodatkowe: Oprócz wyboru kategorii słów, możesz także dostosować inne parametry generacji. Do wyboru masz między innymi:
Liczbę słów do wygenerowania: od jednego do wielu, w zależności od Twoich potrzeb.
Filtr słów według pierwszej litery, ostatniej litery lub długości słowa, co pozwala na jeszcze większe spersonalizowanie wyników.
Proces generowania Po dokonaniu wszystkich wyborów, wystarczy kliknąć przycisk „Generuj”. Słowa zostaną natychmiastowo wygenerowane i wyświetlone na ekranie. Możesz wygenerować nową listę słów tyle razy, ile tylko chcesz.
""", "output_stego_30.wav")
# Odczytywanie

msg2 = extract_message("output_stego_30.wav")
print("Odczytana długa wiadomość z pliku 30sek:", msg2)


#Próba odczytania pliku niezakodowanego
msg3 = extract_message("input_10.wav")
print("Odczytana wiadomość z pliku:", msg3)

# Próba ukrycia 1 MB wiadomości w małym pliku
too_long = "A" * 10**6
hide_message("input_10.wav", too_long, "fail.wav")