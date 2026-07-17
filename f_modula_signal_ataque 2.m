function f_modula_signal_ataque(filename,f_portadora)

%{ Este script carga el archivo .wav de un audio grabado, extrae los datos
% y modula la señal en amplitud a la frecuencia y con la profundidad deseada
% Se realiza un resampling a la frecuencia adecuada para el ADALM.
% Los datos de salida se almacenan en un archivo .mat del mismo nombre.
% Parámetros:
%   - filename: *.wav
%   - f_portadora
%   - fs_final: frecuencia del ADALM
%   - profundidad
%   - guarda_datos
%   - normaliza_audio
%   - escala_audio
%   - V_max
%}

% Borrado inicial
%close all;
% clear all;

% Inicialización
guardar_datos   = false;     % Indica si se guardan o no los datos en .mat
normaliza_audio = true;     % Normalizar para que el máximo sea 1
escala_audio    = true;    % Escalar al máximo de salida del ADALM
V_max           = 5;        % [V] +-5V es el máximo para el ADALM
fs_final        = 75e4;     % Frecuencia de la señal para el ADALM     
%fs_final = 75e3;            
% Parámetros de la portadora
% f_portadora   = 18000;        % [Hz]
profundidad     = 1;            % Profundidad de la modulación

% filename =      ['Bajar_brillo_short.wav'];
% filename =      ['Siri_día_short.wav'];

filefolder = '.\Archivos\Audios\Ataques\'
filename = [filefolder filename];

% Extraigo el nombre del archivo para title
indice_barra    = strfind(filename, '\');
indice_wav      = strfind(filename, '.wav');
name_sin_ruta   = filename(indice_barra(end) + 1 : indice_wav - 1);
%name_sin_ruta   = strrep(name_sin_ruta, '_', '-');

% Señal de entrada
[y,Fs] = audioread(filename);       % Extracción de los datos del .wav
t = 0 : 1/Fs : (length(y) - 1)/Fs;  % Vector de tiempo

y_resample = resample(y,fs_final,Fs);
t_resample = 0 : 1/fs_final : (length(y_resample) -  1)/fs_final;
signal = y_resample';
t = t_resample;

% Generación de la portadora
portadora = sin(2 * pi * f_portadora * t);

% Señal modulada
s_modulada = (1 + profundidad * signal) .* portadora;
% s_modulada = signal;

% Escala de la señal para que llegue a fin de escala
if normaliza_audio
    s_modulada_max = max(s_modulada);
    s_modulada_min = abs(min(s_modulada));
    s_modulada = s_modulada / 2 * max([s_modulada_max, s_modulada_min]); % Es /2 por la modulación 1+señal
end
if escala_audio
    s_modulada_max = max(s_modulada);
    s_modulada_min = abs(min(s_modulada));
    s_modulada = s_modulada.* (V_max) / max([s_modulada_max, s_modulada_min]);
end

%% Representación
% Representación en tiempo de la señal original y la modulada
figure;
subplot(2,1,1);
plot(t, signal, 'b');
title('Señal Original');
xlabel('Tiempo');
ylabel('Amplitud');

subplot(2,1,2);
plot(t, s_modulada, 'r');
title('Señal Modulada');
xlabel('Tiempo');
ylabel('Amplitud');

% Representación en frecuencia de la señal original y la modulada
figure;
subplot(2,1,1);
fft_signal = abs(fftshift(fft(signal)));
plot(linspace(-0.5,0.5,length(s_modulada)) .* Fs / 1e3 , fft_signal,'b');
title('Señal Original');
xlabel('kHz');
ylabel('Amplitud');

subplot(2,1,2);
fft_signal_modulated = abs(fftshift(fft(s_modulada)));
plot(linspace(-0.5,0.5,length(s_modulada)) .* fs_final / 1e3 , fft_signal_modulated,'r');
title('Señal Modulada');
xlabel('kHz');
ylabel('Amplitud');


% Probamos con el Spectrum Analyzer
sadsb = spectrumAnalyzer( ...
    SampleRate=fs_final, ...
    PlotAsTwoSidedSpectrum=false, ...
    YLimits=[-60 30], ...
    NumInputPorts=2);
sadsb(s_modulada',signal');

%% Guardado de los datos
if guardar_datos
    signal_data = s_modulada;
    f_carrier = f_portadora;
    kSps = fs_final/1e3;
    depth = profundidad;
    Fs_audio = Fs;
    save_name = ['datos_' name_sin_ruta '_' num2str(f_portadora/1000) 'k_modulada_p' num2str(profundidad) '_Fs_' num2str(fs_final/1e4) 'e4' '.mat'];
    % save_name = ['datos_' name_sin_ruta '_sin_modular.mat'];
    save_name = [name_sin_ruta '_' num2str(f_portadora/1000) 'kHz.mat'];
    save(save_name,"signal_data","f_carrier","kSps","Fs_audio");
    disp(['Guardado en ' save_name]);
else
    disp('Los datos no se han guardado');
end

end