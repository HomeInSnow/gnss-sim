<!-- Page 1 -->

## Implementation of the new GPS

## L1C signal in a software-defined

## Global Navigation Satellite System

## Receiver

### Into J. A. Pääkkönen

School of Science

Thesis submitted for examination for the degree of Master of Science in Technology. Espoo 8.4.2024

Supervisor

Prof. Visa Koivunen

Advisor

Prof. M. Zahidul H. Bhuiyan


<!-- Page 2 -->

Copyright © 2024 Into J. A. Pääkkönen


<!-- Page 3 -->

Aalto University, P.O. BOX 11000, 00076 AALTO www.aalto.fi Abstract of the master’s thesis

Author Into J. A. Pääkkönen Title Implementation of the new GPS L1C signal in a software-defined Global Navigation Satellite System Receiver Degree programme Master’s programme in engineering physics Major Materials Physics and Quantum Technology Code of major SCI3056 Minor Signal Processing and Data Science Supervisor Prof. Visa Koivunen Advisor Prof. M. Zahidul H. Bhuiyan Date 8.4.2024 Number of pages 90+1 Language English Abstract A growing demand for more robust and accurate global navigation satellite system (GNSS) services has made it necessary to create new and upgrade existing systems with the U.S. operated Global Positioning System (GPS) being no exception. GPS L1C signal defined as part of an on-going GPS modernization effort uses various new techniques to improve the system, including time-multiplexed binary-offset carrier (TMBOC), low-density parity-check (LDPC) forward error correction, and a dedicated pilot channel. To take advantage of the new features, researchers and other GNSS users have a need for new signal processing tools which the thesis aims to address by proposing and testing a complete GPS L1C software-defined receiver. The GPS L1C receiver was developed as part of FGI-GSRx multi-GNSS software receiver by adapting the receivers various signal processing modules for L1C use. Four main processing modules were defined: GPS L1C pilot-only and combined channel acquisition, L1C pilot channel tracking with BOC or TMBOC subcarrier, GPS CNAV-2 navigation message decoding using simple BCH and belief propagation (BP) LDPC decoding methods, and navigation solution computation using a least-squares method. The implemented receiver modules were tested using live and simulated GNSS I/Q data and precision of the receiver was compared to theory. The thesis discusses the implications of the new signal from the theory’s perspective. Thesis’s results demonstrated the acquisition and tracking of live GPS L1C signals with the implemented receiver. It was noticed that live L1C broadcasts are missing CNAV-2 messages as GPS modernization is still under development. CNAV-2 decoding was tested for simulated Gaussian channels at varying signal-to-noise ratios. The receiver obtained a 50% CNAV-2 decoding rate of success between 15.9 and 24.0 dB-Hz C/N0 depending on the message subframe. Positioning performance of the GPS L1C receiver measured using RMS error showed that the implementation achieves a level of precision in-line with theoretical expectations. The results of the thesis validated the proposed receiver and, therefore, the thesis offers a solid foundation for anybody wishing to develop their own GPS L1C receiver in the future.

Keywords GPS, Positioning, Navigation, Timing, Software receiver, Satellite, Communications, Signal processing


<!-- Page 4 -->

Aalto-yliopisto, PL 11000, 00076 AALTO www.aalto.fi Diplomityön tiivistelmä

Tekijä Into J. A. Pääkkönen Työn nimi Uuden GPS L1C satelliittipaikannussignaalin toteuttaminen ohjelmistolla määriteltyyn radiovastaanottimeen Koulutusohjelma Master’s Programme in Engineering Physics Pääaine Materials Physics and Quantum Technology Pääaineen koodi SCI3056 Sivuaine Signal Processing and Data Science Työn valvoja Prof. Visa Koivunen Työn ohjaaja Prof. M. Zahidul H. Bhuiyan Päivämäärä 8.4.2024 Sivumäärä 90+1 Kieli Englanti Tiivistelmä Kasvava kysyntä luotettavampaa ja tarkempaa satelliittipaikannusta kohtaan on tehnyt tarpeelliseksi luoda uusia ja päivittää olemassa olevia satelliittipaikannus järjestelmiä (GNSS). Yhdysvaltalainen GPS on määrittänyt osana modernisointioh jelmaansa uuden GPS L1C-signaalin, joka sisältää ominaisuuksia kuten TMBOC alikanavamodulonnin, BCH- ja LDPC-virheenkorjauskoodit ja erillisen pilottikanavan. Uusien ominaisuuksien hyödyntäminen vaatii tutkijoilta ja muilta GNSS-palveluiden kehittäjiltä uusia työkaluja signaalin prosessointia varten. Opinnäytetyö vastaan tähän tarpeeseen esittelemällä GPS L1C vastaanottimen toteutuksen ohjelmistolla määritellyssä radiossa. GPS L1C ohjelmistovastaanotin kehitettiin osana FGI-GSRx vastaanotinta muok kaamalla ja optimoimalla vastaanottimen moduuleja yhteensopiviksi L1C-signaalin kanssa. Vastaanottimeen määriteltiin neljä päämoduulia: signaalin havaitseminen hyödyntäen joko pilottikanavaa tai pilotti- ja datakanavan yhdistelmää, L1C pilotti kanavan seuranta hyödyntämällä BOC- tai TMBOC-alikanavamodulointia, CNAV-2 viestien BCH- ja LDPC-koodauksen purkaminen, ja navigointiratkaisun laskeminen pienimmän neliösumman menetelmällä. Vastaanotintoteutusta testattiin todellisella ja simuloidulla I/Q-datalla ja paikannuksen tarkkuutta verrattiin teoriaan. Opinnäy tetyö myös syventyi teorian kautta GPS L1C-signaalin merkitykseen tulevaisuudessa. Opinnäytetyön tulokset demonstroivat oikeiden GPS L1C-signaalien havaitse misen ja seurannan toteutetulla ohjelmistovastaanottimella. Samalla huomattiin CNAV-2 viestien puuttuvan nykyisistä L1C-lähetyksistä. Viestien purkamista testat tiin simuloimalla niiden vastaanottoa AWGN-kanavassa eri signaali-kohinasuhteilla. 50% onnistumistodennäköisyys purkamisessa saavutettiin noin 15.9 ja 24.0 dB-Hz C/N0-arvoilla riippuen valitusta alikehyksestä. Vastaanottimella saavutettu paikan nustarkkuus mitattuna RMS-virheellä vertautui hyvin teoreettisiin odotuksiin uudelle signaalille. Opinnäytetyön tulokset osoittivat vastaanottimen toimivuuden ja niinpä työ tarjoaa pohjan muille GPS L1C vastaanottimien kehittäjille tulevaisuudessa. Avainsanat GPS, Paikannus, Navigointi, Ajastaminen, Ohjelmistovastaanotin, Satelliitti, Tietoliikennetekniikka, Signaalinkäsittely


<!-- Page 5 -->

5

### Preface

This thesis is in a way a physics student’s journey into the worlds of satellite navigation and radio receiver technology. The thesis is written from the perspective of my minor subject in Signal Processing and Data Science and it is the final part of my Master of Science degree at The School of Science at Aalto University.

I want to thank my advisor Professor M. Zahidul H. Bhuiyan and supervisor Profes sor Visa Koivunen for their great advice, encouraging comments, and patience with the thesis. I also wish to thank my family, friends, and colleagues at The Department of Navigation and Positioning at The Finnish Geospatial Research Institute who have supported me throughout the thesis project.

Into J. A. Pääkkönen Espoo, April 2024


<!-- Page 6 -->

6

## Contents

Abstract 3

Abstract (in Finnish) 4

Preface 5

Contents 6

Abbreviations 8

1 Introduction 9

2 Global Navigation Satellite System 10 2.1 Fundamentals of GNSS operation . . . . . . . . . . . . . . . . . . . . 11 2.2 GNSS signal structures . . . . . . . . . . . . . . . . . . . . . . . . . . 12 2.3 Global Positioning System (GPS) . . . . . . . . . . . . . . . . . . . . 17 2.4 Global Navigation Satellite System (GLONASS) . . . . . . . . . . . . 20 2.5 BeiDou Navigation Satellite System (BDS) . . . . . . . . . . . . . . . 21 2.6 Galileo . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 24

3 GNSS Receivers and Signal Processing 27 3.1 Receiver front-end . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 27 3.2 GNSS signal acquisition . . . . . . . . . . . . . . . . . . . . . . . . . 29 3.3 GNSS signal tracking . . . . . . . . . . . . . . . . . . . . . . . . . . . 32 3.4 Demodulating and decoding navigation messages . . . . . . . . . . . 35 3.5 Navigation solution computation . . . . . . . . . . . . . . . . . . . . 38

4 GPS L1C Signal 45 4.1 GPS L1C ranging and overlay codes . . . . . . . . . . . . . . . . . . . 46 4.2 TMBOC subcarrier modulation . . . . . . . . . . . . . . . . . . . . . 48 4.3 CNAV-2 navigation message . . . . . . . . . . . . . . . . . . . . . . . 48

5 GPS L1C Receiver Implementation 51 5.1 GPS L1C signal model . . . . . . . . . . . . . . . . . . . . . . . . . . 52 5.2 Signal acquisition . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 52 5.3 Signal tracking . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 55 5.4 CNAV-2 navigation message decoding . . . . . . . . . . . . . . . . . . 59 5.5 Obtaining GPS L1C navigation solutions . . . . . . . . . . . . . . . . 62

6 Experimental Setup 63 6.1 Signal capture with Ettus USRP X310 . . . . . . . . . . . . . . . . . 63 6.2 Signal generation with Safran Skydel GNSS simulator . . . . . . . . . 63 6.3 FGI-GSRx receiver setup . . . . . . . . . . . . . . . . . . . . . . . . . 64


<!-- Page 7 -->

7

7 Results 66 7.1 Acquiring live GPS L1C signals . . . . . . . . . . . . . . . . . . . . . 66 7.2 Tracking live GPS L1C signals . . . . . . . . . . . . . . . . . . . . . . 66 7.3 CNAV-2 decoding with implemented receiver . . . . . . . . . . . . . . 69 7.4 User positioning with simulated GPS L1C signals . . . . . . . . . . . 72

8 Discussion 77 8.1 Implications of GPS L1C signal for future GPS positioning . . . . . . 77 8.2 Impact and limits of the thesis’s results . . . . . . . . . . . . . . . . . 78 8.3 Considering the future development of the GPS L1C receiver . . . . . 79

9 Conclusion 81


<!-- Page 8 -->

8

### Abbreviations

ADC Analog-to-digital Converter AGC Automatic Gain Control ARNS Aeronautical Radio Navigation Service AWGN Additive White Gaussian Noise BDS BeiDou Navigation Satellite System BCH Bose–Chaudhuri–Hocquenghem Codes BOC Binary Offset Carrier BPF Bandpass Filter BPSK Binary Phase-shift Keying CDMA Code-division Multiple Access CRC Cyclic Redundancy Check DFT Discrete Fourier Transform DLL Delay-locked Loop ECEF Earth-centered, Earth-fixed Coordinate System ECI Earth-centered Inertial Coordinate System FDMA Frequency-division Multiple Access FEC Forward Error Correction FFT Fast Fourier Transform FLL Frequency-locked Loop GEO Geostationary Orbit GLRT Generalized Likelihood-ratio Test GNSS Global Navigation Satellite System GPS Global Positioning System ICD Interface Control Document IF Intermediate Frequency IGSO Inclined Geosynchronous Orbit LNA Low-noise Amplifier LDPC Low-density Parity-check MBOC Multiplexed Binary Offset Carrier MEO Medium Earth Orbit NCO Numerically-controlled Oscillator PLL Phase-locked Loop PNT Positioning, Navigation, and Timing PRN Pseudorandom Noise PVT Position, Velocity, and Time QPSK Quadrature phase-shift keying SV Space Vehicle RAAN Right Ascension of the Ascending Node RMS Root Mean Squared RF Radio Frequency TMBOC Time-multiplexed Binary Offset Carrier TOA Time-of-arrival TOF Time-of-flight TOS Time-of-sending VCO Voltage-controlled Oscillator


<!-- Page 9 -->

### 1 Introduction

A global navigation satellite system, or a GNSS, is an ensemble of satellites and supporting ground based infrastructure that provides positioning, navigation, and timing on for terrestrial, maritime, aerial, and even orbital users \[1, p. 6–8\]. The term GNSS is used to refer both collectively and individually to a range of satellite based systems used to achieve navigation on global or regional scale \[2\]. GNS-systems are mainstays of modern information based societies where cheap and fast access to accurate positioning and timing are taken as granted and relied upon. A new GPS L1C signal coming online during the current decade as part of an on going Global Positioning System (GPS) modernization effort is due to offer improved performance over its legacy L1 C/A signal counterpart. The new signal features BOC-type subcarriers that reduce in-band interference and positioning error due to thermal noise, long ranging codes spanning 10 ms, a dataless pilot channel, and forward error correction. The features allow users to benefit from more precise and robust GPS services especially in difficult signal conditions. The modernized signal will bring GPS in-line with the European Galileo and the Chinese BDS-3 systems which utilize similar structures in their corresponding L1 band signals. Signal level interoperability between the systems will ease multi-system receiver development in the future. The scope of the thesis includes a review of contemporary GNS-systems and common GNSS signal structures like PRN codes, navigation messages, and subcarriers. The thesis also looks into GNSS receiver signal processing methods for acquiring, tracking, and utilizing GNSS signals for positioning, navigation, and timing (PNT). The thesis includes a detailed description of the GPS L1C signal definition and proposes a software-defined GPS L1C receiver that is also implemented to FGI-GSRx receiver. FGI-GSRx is a GNSS software receiver that functions by executing a pipeline of signal processing modules implemented as MATLAB functions to produce navigation solutions from raw GNSS I/Q data. The thesis work aims to address a need at the Finnish Geospatial Research institute (FGI) for GPS L1C receiver tools so that the signal can be utilized in future research projects. A plan is to also integrate the MATLAB codes implemented as part of the thesis to an open-source version of FGI-GSRx receiver to provide the L1C processing capabilities to the wider GNSS research community. This contribution can hopefully help many GNSS researchers to start utilizing and testing the new signal as it becomes more widely available during the current decade. The thesis comprises nine chapters starting from this introduction. Chapters 2 and 3 explain background theory on contemporary GNS-systems and GNSS receiver technology respectively. Chapter 4 goes over the definition of GPS L1C signal and chapter 5 explains a L1C receiver design proposed and implemented as part of FGI-GSRx. Chapter 6 details an experimental setup used to validate and test the receiver, with results showcased in chapter 7. Chapter 8 discusses the implications and limitations of the results and the new signal and proposes some ideas for future receiver development. The thesis is closed with a conclusion in chapter 9.


<!-- Page 10 -->

10

### 2 Global Navigation Satellite System

There currently exists four operational global navigation satellite systems: GPS (USA), GLONASS (Russia), BDS (PRC), and Galileo (EU). There also exists two regional navigation satellite systems of QZSS (Japan) and IRNSS (India) which operate on many of the same principles as the four global systems but offer services to limited geographical areas. A GNSS can be divided into three segments: an user segment, a space segment, and a ground or a control segment \[3, p. 3–7\]. Figure 1 illustrates the three segments.

- An user segment consists of the many civilian, commercial, and official users of

a GNSS. The main tool of a GNSS user is a receiver that is a device capable of processing GNSS signals transmitted by satellites and provides the user with position, velocity, and GNSS time estimates \[3, p. 3–7\]. A receiver can be classified based on, e.g., its application or the number of frequencies used.

- A GNSS space segments consists of the satellites of a GNSS which are commonly

referred to as space vehicles (SV) \[3, p. 3–7\]. With few exceptions, the SVs create an one-way downlink to the user segment, which is to say that satellites do not receive anything from the users. For a global system, the space segment is designed to have a core of at least 24 medium earth orbit (MEO) satellites with a few extra in orbit for maintenance and service continuity \[4, 5, 6, 7\].

- A GNSS ground segment monitors, sends data to, and controls SVs to maintain

the system’s services \[3, p. 3–7\]. One critical feature of a GNSS is that satellites broadcast their precise orbital states and clock times to users. This information has to be maintained by the ground segment through monitoring and data uplinks. The ground segment includes, e.g., a master control station, satellite monitoring stations, and communication systems.

User segment Control segment Space segment

Figure 1: Three segments of a GNSS: user, space, and control.


<!-- Page 11 -->

11

2.1 Fundamentals of GNSS operation All GNSS base their operation on a few principles summarized in the following list \[8\]:

- GNSS satellites maintain precise time and orbital state information using on

board atomic clocks, and frequent uplinks from ground segment which monitors the satellites. SVs belonging to a GNSS store information on any clock bias between their internal atomic clocks and a general system time defined by the ground segment.

- Satellites transmit ranging codes which are used by receivers to measure signal

timing and, by extension, distance to satellites. Ranging codes are also used by all GNSS to allow receivers to track and receive data from multiple SVs transmitting on the same frequency band simultaneously using code-division multiple access (CDMA). GLONASS also uses frequency-division multiple access (FDMA) on its legacy signals.

- Satellites transmit navigation messages which are used by receivers for deter

mining satellites’ orbital states and clock times, even without the use of other external information sources. The messages include at least three components: time information and clock corrections used for determining message time of sending, accurate short-term orbital parameters called ephemerides, and a set of non-immediate parameters, e.g., constellation health information and almanac which provides parameters for coarse long-term orbital state prediction.

- GNSS receivers use internal clocks, ranging codes, and times of sending of

received messages to form pseudorange estimates ρ to tracked SVs as

ρ = c(tr − ts),

where tr is the message’s measured time of arrival and ts is the time of sending.

- A receiver computes its position, velocity, and time using received satellite

ephemerides and pseudorange measurements. Ephemerides and measurements have to be available for at least four SVs to solve for three position coordinates and the bias between the receiver’s clock and GNSS system time. A pseudorange model connects pseudorange measurements to receiver and satellite states:

ρ = ||xr − xs|| + c∆t + ε,

where xr is a receiver position vector, xs is a satellite position vector, ∆t is receiver clock bias, and ε includes various ranging errors \[8, p. 76\].

The presented list of basic principles leaves out many important features of modern GNS-systems which contribute to the systems’ performance and robust operation. GNSS technology is already well-matured and a number of additional augmentation and external aiding techniques have been developed to provide improved services


<!-- Page 12 -->

12

for specific applications and operational environments like mobile devices, surveying, and aviation \[9\]. Although an important part of modern GNSS operation, GNSS augmentation shall not be explored in detail during the thesis and the focus will instead be on GNSS positioning, navigation, and timing using information available from GNSS satellites directly using an ordinary receiver.

2.2 GNSS signal structures The purpose of a GNSS signal is to facilitate time and data transfer from GNSS space segment to users. The accuracy of time dissemination is essential for GNSS receivers when it comes to pseudorange estimation as even a slight 1 ns error in timing yields around 0.3 meter ranging error. GNSS signals use a tiered structure to facilitate the simultaneous transfer of timing information using ranging codes and navigation message data \[8, p. 14–17\]. In practice, this is accomplished by mixing together multiple binary sequences at different rates. Figure 2 illustrates a typical GNSS signal structure. The signal in the figure does not match any true GNSS signal but highlights the overall construction of a tiered signal and commonly utilized signal components including navigation messages, pri mary and secondary ranging pseudorandom (PRN) codes, and subcarrier modulation \[8, p. 14–17\]. The following sections explore the different tiers of the signal and their applications. As in any other modern form of radio communication, a GNSS signal is modulated onto a carrier for transmission at a frequency band dedicated to the signal.

2.2.1 Navigation message

Navigation messages are the lowest rate components of GNSS signals. Message symbol rates vary from dozens to hundreds of symbols per second (sps) \[8\]. The word symbol is used to refer to encoded navigation message bits while non-encoded message bits are referred to as bits. Navigation message encoding is used by modern GNS-systems for forward-error correction (FEC) where additional redundancy bits are sent alongside messages. Redundancy bits are used by receivers to find and correct erroneously received data bits in the message. This is especially helpful when a message is received in a covered or otherwise bad signal environment where loss of signal is possible. Information included in navigation message is divided into frames, subframes, and pages that organise the data into smaller usable chunks and may utilize different FEC methods depending on the importance of their contents \[10, 11\].

2.2.2 Ranging codes

Ranging codes form a second layer to a tiered GNSS signal \[8, p. 17–20\]. A typical ranging code chipping rate varies from 500 kilochips per second (kcps) to around 10 Mcps \[10, 11, 12\]. GNSS ranging codes have the dual purpose of facilitating both accurate time dissemination and separation of signals transmitted by different satellites on the same frequency band using direct-sequence CDMA (DS-CDMA). Ranging code pulses are referred to as chips following CDMA terminology.


<!-- Page 13 -->

13

Modulated carrier wave

Subcarrier modulated chips

Ranging code chips

Navigation message symbols Ranging PRN code Subcarrier

Figure 2: Illustration of an example tiered signal used by a GNSS. The ranging code is combined with the navigation message, such that each symbol of the message spans one entire ranging code length. Subcarrier modulation is added to the resulting binary sequence before its phase modulation onto a carrier. The figure’s time scaling and the PRN code length do not match actual GNSS signals.

The fine scale estimation of signal’s time of arrival within a GNSS receiver is based on correlating a local replica ranging code with a captured signal. The ranging code is a pseudorandom (PRN) sequence with an autocorrelation function (ACF) that is peaked at zero delay and is ideally zero everywhere else. During signal tracking, a local replica code is iteratively delayed or advanced based on measured ACF gradient such the code stays synchronized to a matching code transmitted from a satellite. As such, the design of ranging codes plays an important role in GNSS timing and positioning accuracy. DS-CDMA in a GNSS achieved by assigning a unique ranging PRN code for each SV in the system. Cross-correlation between the assigned codes are ideally zero at all delay values and correlating an input signal with a replica PRN code therefore provides processing gain only for the signal sent by the corresponding SV. Long correlation times, typically between 1 to 20 ms, are needed to overcome the weakness of GNSS signals buried below a background noise floor. A typical minimum received terrestrial signal power of a GNSS signal is between -165 and -155 dBW \[10, 11, 12\].

![page 13](images/image-001.png)

![page 13](images/image-002.png)

![page 13](images/image-003.png)


<!-- Page 14 -->

14

PRN code families used by GNS-systems include M-sequence, Gold, Kasami, Weil, and pseudorandom memory codes \[8, p. 18\]. Longer PRN code generally offer better cross-correlation properties for DS-CDMA but may necessitate the use of longer signal correlation times \[13\]. On the other hand, a faster chipping rate allows for improved resolution in timing and consequently a higher obtainable precision in positioning while requiring a wider receiver bandwidth that demands more processing power and may make the signal more vulnerable against in-band interference \[14, p. 196\].

2.2.3 Primary and secondary codes

Many modern GNSS signals are modulated by additional lower rate secondary codes that can serve different purposes depending on their designs. Some secondary codes are used for navigation message symbol or frame level synchronization in a receiver \[15, 16\]. A secondary code spanning a long enough period can also be used to quickly infer the sending time of a signals in a receiver that is already roughly synchronized to GNSS system time. A longer code duration allows for larger time offset between the receiver and system time but may increase the waiting time required to obtain a time synchronization. Another use for secondary codes is to extend the total length of PRN codes for improved DS-CDMA cross-correlation properties. Just like their primary code counterparts, secondary codes assigned to different satellites can be mutually un correlated. Combining secondary and primary codes such that each secondary code chip spans one whole primary code sequence results in a tiered PRN code of length Nc = Np × Ns, where Np is the primary code length and Ns is the secondary code length \[17\]. The longer code provides better DS-CDMA cross-correlation properties and interference protection but does not necessitate an increased correlation time as it is still possible to only utilize the primary codes. A secondary code will add an extra layer of modulation to a signal which needs to be considered when correlating a signal over multiple primary codes.

2.2.4 Carrier modulation

GNSS ranging codes and navigation messages are modulate onto a carrier for trans mission. GNSS carrier frequencies lie in the lower and upper L-bands located between 1 and 2 GHz \[8, p. 7\]. A GNSS refers to the frequency bands of its signals using numbers, e.g., L1 C/A, L2C, and L5 for GPS and E1, E5, and E6 for Galileo. The L-bands have qualities which makes them suitable for GNSS use such as little effect from weather and manageable levels of atmospheric disturbance in general. All contemporary GNSS use phase-shift keying for encoding ranging code and navigation message information onto a carrier. Binary phase-shift keying (BPSK) is a modulation technique utilized by most legacy GNSS signals \[8, p. 9–11\]. In BPSK, transmitted binary sequences modulate the phase of a carrier wave such that the zeros and ones are antiphase or 180◦ apart from each other. This provides the maximum phase separation between symbols which helps to minimize symbol error rate over a communication channel.


<!-- Page 15 -->

15

GNSS signals also take advantage of the fact that two carrier waves transmitted at the same frequency but 90◦ apart in phase are orthogonal and can therefore be separated easily \[8, p. 13\]. The two waves are referred to as in-phase (I) and quadrature phase (Q) components and are generally used in GNSS to transmit separate ranging codes that belong to different signals. The same GNSS signal can also have two components that are transmitted in-phase and quadrature-phase in which case the signal modulation is called quadrature phase-shift keying (QPSK). Figure 3 shows a simple QPSK modulator for two binary streams.

90◦ phase shift Signal out Carrier I

Q

Figure 3: Two binary streams I and Q are phase modulated with 90◦ offset.

2.2.5 Subcarrier modulation

Subcarrier modulation refers to additional square wave modulation added to a GNSS signal for the purpose of shifting the signal’s spectrum away from its center frequency \[8, p. 11\]. This reduces cross-signal interference from other GNSS signals transmitted on the same band and increases the signal’s effective bandwidth allowing for more precise timing akin to using a higher code chipping rate \[13\]. Subcarrier modulation used in GNSS is based on binary-offset carrier (BOC) modulation with GPS, GLONASS, Galileo and BeiDou employing various versions of it on a number of signals. BOC modulation is similar to Manchester coding used to aid clock recovery in digital communication and storage \[18\]. BOC modulation can be defined mathematically by taking the sign of a sine or a cosine function of a certain frequency \[19\]. Let fc = 1/Tc be the code chipping rate of a GNSS ranging code and fs be the frequency of BOC modulation applied to the code. Sine and cosine BOC sequences are defined as

ssinBOC(fs,fc)(t) = −sign (sin(2πfs × t)) (1) scosBOC(fs,fc)(t) = −sign (cos(2πfs × t)). (2)

Equations (1) and (2) follow signal phase definition set in GPS IS-800-ICD interface control document and hence the minus in front \[11\]. A generated BOC sequence is combined with a ranging code on a per-chip basis, dividing each code chip into n = 2fs/fc subcarrier pulses, and the resulting signal is BPSK or QPSK modulated onto a carrier. In a GNSS, subcarrier frequencies and ranging code rates are multiples of a reference frequency fref = 1.023 MHz and hence


<!-- Page 16 -->

16

various rate BPSK and BOC modulations can be written as

BPSK(nc) ≡ BPSK(nc × fref ) = BPSK(fc) BOC(ns, nc) ≡ BOC(ns × fref , nc × fref ) = BOC(fs, fc).

Figure 4 shows examples of sinBOC and cosBOC sequences over one ranging code chip period t ∈ \[0, Tc\] while figure 5 shows power spectral densities (PSD) of BPSK, sinBOC, and cosBOC modulated infinite random uncorrelated equiprobable binary sequences. The PSDs approximate the spectra of GNSS signals but are not exact since the navigation messages and the PRN codes of the signals are not truly random. For a more in-depth look into BOC modulation and derivation of formulas for the PSDs, readers are referred to a 2001 journal paper by John W. Betz \[20\].

1

0 BPSK(1) sinBOC(1, 1) cosBOC(1, 1) sinBOC(6, 1)

t/Tc t/Tc t/Tc t/Tc 0 1 0 1 0 1 0 1

Figure 4: BPSK, sinBOC(1,1), cosBOC(1,1), and sinBOC(6,1) pulses plotted over one primary code chip period.

−8 −7 −6 −5 −4 −3 −2 −1 0 1 2 3 4 5 6 7 8 −100 −90 −80 −70 −60

Frequency \[MHz\] BPSK(1) sinBOC(1,1) cosBOC(1,1) sinBOC(6,1)

Figure 5: Baseband power spectral densities of an infinite uncorrelated equiprob able binary sequences modulated using BPSK(1), sinBOC(1,1), cosBOC(1,1), or sinBOC(6,1).


<!-- Page 17 -->

17

2.2.6 Data and pilot channels

Many modern GNSS signals include complementary pilot channels which are similar to the already discussed data channels with the exception that the navigation messages are omitted \[8, p. 9\]. Pilot and data channels are typically transmitted with unique PRN codes at either in-phase or quadrature-phase, which provides separate access to the components. The use of a pilot channel helps receivers to acquire and track of signals as repeating and deterministic ranging codes that lack any phase modulation due to data symbols can be coherently integrated over multiple ranging codes for improved signal-to-noise ratio. Typically, pilot channels also employ secondary codes to break the repeating code pattern for reduced cross-signal interference. Coherent and non-coherent signal integration is discussed further in the thesis chapter 3 on GNSS receivers.

2.3 Global Positioning System (GPS) Global Positioning System (GPS) is a global navigation satellite system developed and operated by the U.S. Department of Defence \[4\]. GPS was the first GNSS to provide public access to satellite positioning and timing with its standard positioning service, although the service was intentionally degraded before the 2000s using a method called selective availability \[21\]. According to European GNSS Agency user technology report (2020), GPS is the most utilized GNSS constellation to date although most modern GNSS receivers are capable of utilizing all four of the main GNS-systems \[22\].

2.3.1 GPS signal plan

GPS satellites broadcast ranging codes and navigation messages on three frequency bands referred to as L1, L2, and L5 that are centered around frequencies 1575.42 MHz, 1227.60 MHz, and 1176.45 MHz respectively. All of the frequencies are multiples of 10.23 MHz which is the standard reference frequency produced by atomic clock systems on-board GPS satellites \[23\]. On the three carrier bands, there exists a total of six different ranging codes: legacy C/A and P(Y), and modernized L2C, M-code, L5, and L1C. The different GPS signals are summarized in table 1 and in the following list:

- C/A code is the original standard positioning service code made available for

civilian navigation. C/A stands for coarse/acquisition which highlights its role as the less accurate counterpart of the higher rate precision P-code that could be acquired using the C/A. C/A code is transmitted on the L1 band and carries a legacy navigation message (LNAV). As a standalone signal it is typically referred to as L1 C/A. The navigation message is modulated on to a 1023 chip long C/A Gold code such that each symbol is spanned by one whole code period of 1 ms.

- Precision P(Y) code is the second original code present of GPS and it is

broadcasted on both L1 and L2 bands to facilitate dual frequency positioning


<!-- Page 18 -->

18

\[8, p. 98\]. Ionosphere is often the largest individual source of timing bias for a GNSS, but its effects can be compensated for using pseudorange estimates from two or more separate frequency bands \[24\]. P(Y) code is transmitted at a high rate of 10.23 Mcps and can provide better timing precision than L1 C/A. P(Y) code combines a week-long PRN P-code that is publicly available and an authorized anti-spoofing scrambling code which prevents non-military user from fully utilizing the signal. Certain features of the code have been exploited by non-military users in so-called codeless receivers \[25\].

- L2C is the second civil signal transmitted from GPS satellites. It offers upgraded

service capabilities over L1 C/A such as FEC and a pilot component \[14, p. 145– 146\]. With L2C, civilian users have the capability to exploit dual-frequency ionospheric corrections. L2C code is also much longer than C/A, which provides both better cross-correlation properties and interference protection. The L2C code is split into two parts, a 10230-chip long L2CM code and a 767250 chip long L2CL code which are time multiplexed together. A civil navigation message (CNAV) is modulated onto the L2C signal such that each message symbol spans one L2CM sequence. Unlike the L1 band, the L2 band is not allocated for the Aeronautical Radio Navigation Service (ARNS) and L2C cannot therefore be used in critical safety-of-life applications like aviation.

- M-code is a modernized encrypted signal designed for military use by the U.S.

department of defence. It is meant to eventually replace P(Y) and includes upgrades to, e.g., signal power, anti-jam features, spectral isolation, signal authentication, and confidentiality \[14, p. 148–150\]\[26\]. Like the P(Y), M-code is transmitted on both L1 and L2 bands.

- L5 refers both to a navigation signal transmitted by GPS satellites and to

the RF band that the signal is transmitted on. L5 is designed especially for dual-band aviation use alongside L1 C/A as both signals are part of the ARNS designated section of the L-band \[8, p. 170\]. Primary ranging codes of GPS L5 are 10230 chip long and produced by combining multiple M-sequences. The signal also includes a 10 or 20 chip long Neuman-Hoffman secondary code. Compared to L1 C/A and L2C, the L5 signal has a higher code chipping rate of 10.23 MHz, lower RF frequency, a quadrature phase pilot channel, and is transmitted at higher power, which together provide more precise and reliable service, better multipath rejection, and better surface penetration for indoor applications. However, the higher chipping rate also requires more processing power due to the increased signal bandwidth.

- L1C is the newest GPS signal under commission. The adoption of L1C is still in

its very early stages and no operational PNT service based on L1C is available at the time of writing the thesis due to a low number of L1C capable SVs in orbit and missing navigation message broadcasts. L1C has been designed to be interoperable with Galileo and BeiDou L1-band counterpart signals and to provide more reliable service in covered environments such as cities \[27\]. GPS L1C signal structure is covered in detail during chapter 4.


<!-- Page 19 -->

19

Band Center freq. \[MHz\] Signal Reference bandwidth \[MHz\] Phase Modulation type

C/A Q BPSK(1) P(Y) 20.46 or 30.69 I BPSK(10) L1C 30.69 I TMBOC(6,1,1/11) L1 1575.42

M-code NA NA\*\* sinBOC(10,5) P(Y) I BPSK(10) L2C 20.46 or L2 1227.60 30.69 Varies\* BPSK(1) M-code NA NA\*\* sinBOC(10,5) L5 1176.45 L5 24 I & Q QPSK(10)

Table 1: GPS signal plan includes L1 C/A, P(Y), L2C , L5, and L1C signals \[11, 28, 29, 30\]. Reference bandwidths of the L1 and L2 band signals depend on the GPS SV block number. \*L2C phase in relation to P(Y) can be either in-phase or quadrature-phase. \*\*M-code may be transmitted partly or fully by a separate antenna network on-board GPS satellites \[30\].

2.3.2 GPS space segment

A baseline GPS constellation consists of 24 satellites situated on approximately circular medium earth orbits on six orbital planes labeled from A to F \[4\]. All of the orbits share the same height of around 20 200 km and an inclination angle of around 55◦ measured from the equator. A large inclination angle is required for the GNSS to provide services to polar regions. Longitudes of ascending node of the orbits span a full circle and are separated by a constant value of 60◦ . Each orbital plane includes four satellites at different mean anomalies such that a global coverage across Earth’s surface is achieved. Initial operational capability of GPS was achieved in 1993 with 24 satellites transmitting C/A and P(Y) codes on the L1 and L2 bands. GPS SVs are designed and launched in blocks as summarized in 2.

Block Years launched No. launched No. failures Operational in April 2023 Introduced signals I 1978–1985 11 1 0 L1 C/A, P(Y) II 1989–1990 9 0 0 - IIA 1990–1997 19 0 0 - IIR 1997–2004 13 1 6 - IIR-M 2005–2009 8 0 7 L2C, M-code IIF 2010–2016 12 0 12 L5 IIIA/F 2018– 6 0 6 L1C

Table 2: Number of launched and operational GPS satellites according to their block designation\[31, 32\].

For a long time now, GPS constellation has included extra satellites for redundancy and, n 2011, US Air Force launched an extended GPS constellation standard called


<!-- Page 20 -->

20

Expandable 24 \[33\]. The new standard increased the number of SVs on each orbital plane from four to five and includes a total of 30 orbital slots. As of April 12, 2023, there were 31 operational GPS satellites in orbit \[4\]. The average number of satellites visible to a user in an open environment is from 8 to 10 depending on the user’s coordinates \[34\].

2.4 Global Navigation Satellite System (GLONASS) GLONASS is a GNSS developed originally by the Soviet Union and later by the Russian Federation. Starting in the 1970s, GLONASS was developed concurrently with GPS by the soviets, but the official commissioning of the system fell into the hands of the Russian federation after the dissolution of the USSR in 1991 \[14, p. 8\]. GLONASS was declared operational in September 1993 with 12 satellites in orbit \[35\]. A full 24 SV constellation was achieved during December 1995, but the system soon fell into disrepair due to economic troubles faced by the Russian federation during its early years. In August 2001, the system restoration of GLONASS was made a priority of the Russian state for ten years between 2002 and 2011, with modernized GLONASS-M and GLONASS-K satellites replacing the older and then mostly defunct originals \[36\]. In 2007, GLONASS civil signals were declared open and free to use for all \[37\].

2.4.1 GLONASS signal plan

GLONASS operates on three carrier bands referred to as L1, L2, and L3 \[38\]. Unlike GPS, the codes transmitted on the same band do not necessarily share the same center frequency as GLONASS uses two different multi-access techniques of FDMA and CDMA. Legacy GLONASS signals use FDMA technique where each SV in the constellation transmits one common PRN ranging code on the L1 and L2 bands but at a slightly different carrier frequency. Newer GLONASS-M and all GLONASS-K satellites transmit CDMA signals on the L3 band also and even newer GLONASS-K2 satellites are due to add CDMA signals to L1 and L2 bands as well. Open civil navigation signal transmitted from current and planned future GLONASS satellites are listed in table 3.

Band Signal Center freq. \[MHz\] Primary PRN code (length) Modulation type

FDMA 1602 +0.5625n M-sequence(511) BPSK(1/2) L1 CDMA 1600.995 Data Gold(1023) Pilot Kasami(4092) Data BPSK(1/2) Pilot BOC(1,1/2) FDMA 1246 + 0.4375n M-sequence(511) BPSK(1/2) L2 CDMA 1248.06 Gold(10230) Pilot BOC(1,1/2) L3 CDMA 1202.025 Kasami(10230) QPSK(10)

Table 3: Open signals broadcasted from GLONASS satellites \[12, 39, 40, 41\].

GLONASS uses 14 frequency channels in its L1 and L2 FDMA schemes \[38\]. A


<!-- Page 21 -->

21

full GLONASS constellation includes 24 satellites meaning that some of the SVs have to inevitably share a channel. Unless the issue is properly cared for, two satellites transmitting the same ranging codes on the same carrier band can lead to serious interference and the inability of receivers to track one or both satellites. The solution adopted by GLONASS is to assign a shared frequency channel to two antipodal satellites with a 180 ◦ difference between their anomalies. This physically isolates the signals transmitted by the satellites so no user can receive them simultaneously.

2.4.2 GLONASS space segment

A full nominal GLONASS constellation consists of 24 satellites \[5\] at around 19 100 km altitude. The satellites are situated on three orbital planes with longitudes of ascending node separated by 120◦ . Each orbital plane contains eight SVs at 45◦ true anomaly intervals. The orbital planes have an inclination angle of 64/8 ± 3 as measured from the equator which is slightly higher than with GPS. From a purely geometric point of view, the higher inclination angle provides better service coverage to polar regions. Table 4 lists different GLONASS satellite blocks and their periods of launch.

Block Years launched No. launched No. failures Operational in Nov. 2023 Introduced open signals GLONASS (11F654) 1982–2005 87 6 0 L1 FDMA

GLONASS-M (14F17/113) 2001– 52 6 21 L2 FDMA

GLONASS-K (14F143) 2011– 5 0 3 L2 CDMA\* L3 CDMA GLONASS-K2 (14F160/170) 2023– 1 0 0 L1 CDMA

Table 4: Launched GLONASS satellites and operational status in November 2023. \*The first L2 CDMA capable satellite was Kosmos 2559, the fifth GLONASS-K satellite, launched in 2022 \[42, 43\].

2.5 BeiDou Navigation Satellite System (BDS) BeiDou Navigation Satellite System (BDS) is a GNSS developed and operated by the People’s Republic of China. Unlike the previously discussed GPS and GLONASS, BeiDou includes geostationary orbit (GEO) and inclined geosynchronous orbit (IGSO) satellites alongside a typical MEO constellation \[44\]. BDS provides various services for civilian and authorized users both globally and specifically to East Asia region. Development of first generation BeiDou-1 program started officially in 1993 with a goal to provide regional navigational capabilities independent of GPS and GLONASS for the PRC \[45\]. The original system was based on a Twinsat concept where mere two satellites were used to solve for user’s altitude, longitude, and latitude with the help of territorial maps. The system was operational between 2000 and 2010 with


<!-- Page 22 -->

22

four GEO satellites in orbit, two of which were kept as spares. While the system was very cheap to maintain, it had limited usability due to a requirement for users to actively communicate with control stations using encrypted satellite links. The BeiDou-1 concept was eventually expanded in 2006 when the PRC announced a more traditional BeiDou Navigation Satellite System, also referred to as Compass or BeiDou-2. The second-generation system provides regional services and was quickly developed into a similar but upgraded BDS-3 which has global coverage. The BDS-3 constellation was officially finalized in 2020 \[7\]. The system provides the following services:

- Radio satellite navigation service (RNSS) offers typical GNSS PNT services to

users. RNSS signals provide both an open service and an encrypted authorized service.

- Global Short Message Communication (GSMC) is a worldwide satellite com

munications link.

- International Search And Rescue (SAR) is BDS’s contribution to COSPAS

SARSAT search-and-rescue system discussed briefly alongside Galileo system’s SAR service in the later section 2.6.

- Satellite-based Augmentation System (SBAS) provides improved GNSS service

for East and South Asia regions based on differential GNSS (DGNSS). DGNSS greatly improves PNT accuracy using a wide area reference station network which monitors GNSS signals and compares them to expected observations based on the stations’ location. Differential corrections are formulated from differences between the expected and the observed signals. In a SBAS, a satellite link is used to transmit the differential corrections to users. Similar systems around the globe are WAAS in North-America, EGNOS in Europe, MSAS in Japan, and GAGAN in India.

- Ground augmentation service (GAS) is an DGNSS augmentation service similar

to BDS SBAS with the exception that differential corrections are distributed to users using ground-based communications links.

- Precise Point Positioning (PPP) offers high-rate orbit and clock corrections

for GPS, GLONASS, Galileo, and BDS satellites to greatly improve GNSS positioning and timing accuracy in East Asia. PPP data is broadcasted from three GEO satellites located above the region.

- Regional Short Message Communication (RSMC) is a regional satellite com

munications link operational in China and its surrounding regions.

2.5.1 BDS-3 Open Service signal plan

The BeiDou satellites transmit five unique signals on three different bands referred to as B1, B2 and B3 summarized in table 5. All of the signals include the typical ranging codes and navigation messages. The newest B1C signal also includes a


<!-- Page 23 -->

23

dedicated pilot channel and a BOC-type subcarrier. BDS B1C signal is designed to be interoperable with GPS L1C and Galileo E1 OS signals with a shared center frequency and similar modulation scheme. The common signal designs facilitate interoperability between the systems as a multi-constellation receivers can utilize the same front-end components for the three L1 band signals.

Signal Center freq. \[MHz\] Reference bandwidth \[MHz\] Broadcasting satellites Primary PRN code (length) Modulation type

B1C 1575.42 32.736 IGSO, MEO Weil(10230) QMBOC (6,1,1/11) B2a 1176.45 20.460 IGSO, MEO Gold(10230) BPSK(10) B2b 1207.14 20.460 IGSO, MEO Gold(10230) BPSK(10)

B1I 1561.098 4.092 GEO, IGSO, MEO Gold(2046) BPSK(2)

B3I 1268.52 20.46 GEO, IGSO, MEO Gold(10230) BPSK(10)

Table 5: BeiDou-3 Open service navigation signal specifications \[46, 47, 48, 49, 50\].

2.5.2 BeiDou space segment

A nominal BDS-3 constellation consists of 3 GEO, 3 IGSO, and 24 MEO satellites. The geostationary orbits have an altitude of 35 800 km and the satellites are situated above longitudes 80◦ E, 110.5

- E, and 140◦ E \[7\]. The BDS IGSO satellites operate at

the same altitude as GEO but at a 55◦ inclination angle. The 24 BDS-3 MEO orbits are distributed on three orbital planes with 55◦ inclination angles and longitudes of ascending nodes separated by a constant 120◦ . Nominal MEO satellite altitude is around 21 500 km. As of July 2023, the third generation BeiDou constellation is fully operational with 4 GEO, 3 IGSO, and 24 MEO BDS-3 satellites in orbit alongside 5 GEO, 7 IGSO, and 3 MEO BDS-2 satellites \[51\]. The current and previously operational BDS satellites are summarised in table 6.


<!-- Page 24 -->

24

Constellation Years launched No. launched No. failures Operational in Nov. 2023 BeiDou-1 2000–2007 4 0 0 BDS-2 MEO 2007–2012 5 0 3 BDS-2 GEO 2009–2019 8 0 5 BDS-2 IGSO 2010–2018 7 0 7 BDS-3 MEO-S 2015–2016 3 0 0 BDS-3 IGSO-S 2015 2 0 0 BDS-3 MEO 2017-2023 26 0 24 BDS-3 GEO 2018– 4 0 4 BDS-3 IGSO 2019 3 0 3

Table 6: Launched BeiDou satellites \[51, 52\]. BDS-3 IGSO-S and MEO-S are experimental.

2.6 Galileo Galileo is an European global satellite navigation system commissioned and owned by the European Commission, developed and created by the European Space Agency (ESA), and operated by the European Union Agency for Space Programme (EUSPA). A fully operational first generation Galileo constellation supports six distinct services for civil, commercial, and official user. These are the Open Service (OS) and its navigation message authentication (OSNMA), Public Regulated Service (PRS), High Accuracy Service (HAS), Commercial Authentication Service (CAS), and Search and Rescue Service (SAR) \[53\]. The services are explained briefly in the following list:

- Galileo OS is a basic navigation service broadcasting public ranging codes and

navigation messages on two frequency bands. The Open Service also offers an public navigation message authentication tool in OSNMA which helps receivers avoid interpreting navigation messages that have been tampered with or which are not originally from Galileo satellites.

- Galileo PRS is a positioning and timing service designed to be resilient against

service degradation and malicious interference. PRS is encrypted and only available for government-authorised users within the EU. Examples of users include fire brigades, border control, search and rescue, and humanitarian aid.

- Galileo HAS service provides free-to-access orbital, clock, code bias and phase

bias corrections meant to improve the accuracy of Galileo and GPS services through Precise Point Positioning (PPP). The designed horizontal positioning accuracy of a HAS solution is around 20 cm.

- Galileo CAS is a complementary open service authentication tool offered for

commercial users exclusively.


<!-- Page 25 -->

25

- Galileo SAR is Galileo’s contribution to COSPAS-SARSAT search and rescue

system that also includes GPS, GLONASS, and BDS satellites \[54\]. COSPAS SARSAT transponders mounted on satellites listen to calls from terrestrial and maritime SAR distress beacons and re-transmits them to alert SAR coordination centers. The system’s MEOSAR segment, consisting of equipment mounted on GNSS satellites, facilitates localization of distress calls and provides near constant worldwide coverage.

2.6.1 Galileo Open Service signal plan

Galileo Open Service uses four signals that are sent at four carrier bands referred to as E1 (1575.42 MHz), E5 (1191.795 MHz), E5a (1176.45 MHz), E5b (1207.14 MHz) \[10\]. All of the signals include data and pilot channels and utilize DS-CDMA for multi-access and ranging. E5 signal is the result of in-phase and quadrature phase components of E5a and E5b being multiplexed together using a method referred to as Alternative BOC (AltBOC). The resulting double wide band signal is transmitted at the E5 frequency 1191.795 MHz. AltBOC modulated signal can be split into two sub-bands centered around E5a and E5b frequencies and the sub-bans may be received independently. Summary of the signals is shown in table 7. Galileo also includes secondary codes and pilot channels on its signals.

Band Center freq. \[MHz\] Service Reference bandwidth \[MHz\] Primary PRN code (length) Modulation type

OS 24.552 Memory code (4092) CBOC(6,1,1/11) E1 1575.420 PRS N/A N/A cosBOC(10,5)

E5 1191.795 OS 51.150 M-sequence (10230) AltBOC(15,10)

E5a 1176.450 OS 20.460 M-sequence (10230) AltBOC(15,10)

E5b 1207.140 OS 20.460 M-sequence (10230) AltBOC(15,10)

HAS CAS 40.920 Memory code (5115) BPSK(5) E6 1278.750 PRS N/A N/A cosBOC(10,5)

Table 7: Galileo signal plan: bands, services and signal modulation\[10, 55\].

Galileo has been designed to be highly interoperable with GPS as both systems’ geographic reference frames and system times are similar enough to allow receivers to supplement information from one system to the other without the use of coordinate transforms \[56\]. Galileo E1 and E5a have near identical PSDs to GPS L1C and L5 respectively, which allows receivers to utilize many of the same front-end components for receiving the signals from both systems.


<!-- Page 26 -->

26

2.6.2 Galileo space segment

A nominal Galileo constellation consists of 24 MEO satellites on three orbital planes with inclination angles of 56◦ \[6\]. Each orbital plane includes 8 satellites with a constant 45◦ true anomaly spacing. Longitudes of ascending nodes for the orbits are 120◦ apart similar to GLONASS and BDS. The nominal altitude of the orbits is around 23 200 km. The constellation’s geometry repeats itself every 10 sidereal days. Galileo also includes six auxiliary satellites which can be assigned to vacant operational slots in the constellation in case of a SV malfunction or maintenance \[57\]. The launching of first generation Galileo satellites is still under way as of 17 Nov. 2023 with the constellation having 23 operational SVs according to European GNSS Service Centre \[58\]. Table 8 summarizes the Galileo satellite generations.

Satellite Years launched No. launched No. failures Operational in Nov. 2023 Introduced signals GIOVE-A/B 2005, 2008 2 0 0 E1, E5, E5a, E5b, E6

Galileo-IOV 2011-2012 4 0 3 -

Galileo-FOC 2014-2021 24 2 20 - Galileo-G2G 2024- 0 0 0 -

Table 8: Launched Galileo in-orbit validation (GIOVE and IOV), full-operational capacity (FOC), and future second generation G2G satellites \[58, 59\].


<!-- Page 27 -->

27

### 3 GNSS Receivers and Signal Processing

A GNSS receiver is a tool needed by all GNSS users to utilize and benefit from GNSS services. A GNSS receiver can be classified based on, e.g., its capabilities, application, and implementation:

- Number of frequencies utilized by a GNSS receiver may vary. Receivers are com

monly categorized into single-frequency, dual-frequency, and multi-frequency receivers based on how many frequency bands are available. The ability to compensate for ionospheric pseudorange bias is a major advantage of using a dual- or multi-frequency receiver over a single-frequency one. Dual- and multi frequency receivers can also benefit from added resilience against interference or service degradation.

- A GNSS receiver using more than one constellation, e.g., both GPS and Galileo,

may be referred to as a multi-constellation receiver. A well implemented multi-constellation solution benefits especially from the larger number of usable satellites in the sky which improves service continuity and PNT accuracy due to a better overall constellation geometry \[60\]. The larger number of satellites may also facilitate GNSS operation in environments with limited visibility to the sky \[61\].

- Applications of GNSS receivers can vary. Many receivers are designed with a

specific use case in mind or are integrated into devices like mobile phones or vehicles. The application domain can set both operational and legal standards that have to be met by the receiver’s design. Some examples include accuracy required for surveying or reliability required for aviation use.

- The implementation of a GNSS receiver can vary. Modern GNSS receivers use a

front-end module that conditions an analog input signal and converts it to digital \[14, p. 235-236\]. Further digital signal processing (DSP) is implemented in a dedicated hardware, e.g., ASIC or FPGA, or in software run on a microprocessor like a CPU or a digital signal processor \[62\]. Typical commercially available receivers include all their components in a single chip or as part of a SoC. A receiver with DSP implemented in software may be called a software receiver.

3.1 Receiver front-end A receiver front-end is used to condition an input analog bandpass RF signal captured by an antenna to intermediate frequency (IF) equivalent while filtering away off-band components and applying low-noise amplification to boost usable signal power \[8, ch. 1.43\]. Practically all GNSS front-ends convert the analog IF signals to digital using analog-to-digital converter (ADC) for further processing \[14, ch. 5.12\]. The receiver front-end can be divided into a few main components:

- Front-end bandpass filters (BPF) are used to reject noise and interfering

signals that exist outside the RF band of the received signal. Two important


<!-- Page 28 -->

28

characteristics of a bandpass filter are bandwidth and selectivity. Bandwidth describes the width of the frequency band that can pass through the filter, while selectivity describes how quickly attenuation increases in the filter’s transition bands. High selectivity is desirable for good off-band rejection but comes with added filter complexity. In general, a low filter bandwidth which encompasses enough of a GNSS signal’s RF band to achieve a required precision is used for performance and good off-band rejection properties.

- Front-end low-noise amplifiers (LNA) are used to increase received signal power

to compensate for transmission losses. The use of an amplifier provides both gain and additional noise that can negatively impact signal-to-noise ratio. For this reason, a LNA is usually the first component of a front-end after initial RF filtering which may be required to prevent the amplifier from becoming saturated from off-band interference. A LNA can also be integrated into a GNSS antenna if there is a long transmission line between the antenna and the receiver.

- Down-conversion is used to shift an RF signal form its carrier band to a desired

IF frequency while preserving any signal modulation containing transmitted information. Down-conversion can be achieved through heterodyning where a received RF signal centered around frequency fRF is mixed with a local oscillator of frequency fLO in a non-linear device like a transistor or a diode. The mixer output includes not only the original frequency components but also two heterodynes at frequencies |fRF ± fLO| and possibly other higher order intermodulation products. The lower heterodyne band centered around fIF = |fRF −fLO| is of most interest as it contains a down-converted IF version of the RF signal. A heterodyne receiver also down-converts an image-band that is a replica of the RF band mirrored according to the LO frequency. The image must be filtered away to avoid introducing off-band interference. Heterodyne receivers can convert RF signal to baseband using multiple steps to ease complexity associated with designing image rejection filters. However, multistage heterodyne receivers come with drawbacks like low flexibility for multi-frequency use, difficulties in implementing image rejection filters in integrated circuits, and high power consumption \[63\]. To overcome these issues, modern GNSS receivers typically utilize what are known as direct-conversion receivers (DCR) or low-IF receivers which down-convert RF signals to baseband or low IF in a single stage. A receiver with zero IF frequency removes the image band problem but can be vulnerable against DC bias or 1/f noise. Figure 6 shows a block diagram of a single-stage heterodyne front-end.

- Analog-to-digital conversion (ADC) is used for sampling and quantizing an ana

log IF signal to a digital equivalent \[8, p. 35–36\]. ADC introduces quantization noise due to the finite number of bits used to represent digital samples. The added noise is dependent on sample bit size as well as a chosen quantization interval. 1-bit and 2-bit ADCs are widely used in commercial GNSS receivers


<!-- Page 29 -->

29

due to the relative weakness of GNSS signals. Quantization noise beyond four bit quantization can usually be considered negligible \[8, p. 36\]. Analog-to-digital converter with quantization level higher than just one bit is typically paired with an automatic gain control (AGC) which is a feedback control device that attempts to keep the ratio between ADC quantization interval and receiver noise at a constant optimal value \[64\]. AGC can be implemented by, e.g., estimating signal RMS noise based on input samples and controlling either front-end LNA gain or quantization interval of the ADC.

RF in BPF LNA Mixer

VCO BPF AGC ADC IF out

Figure 6: Block diagram of a single stage heterodyne front-end.

3.2 GNSS signal acquisition Signal acquisition serves two purposes within a GNSS receiver: detection of satellites present in the sky above an antenna, and coarse estimation of Doppler shift and code timing delay needed to initialize signal tracking \[8, p. 38–41\]. A digitized down-converted baseband signal model is presented to better describe the signal acquisition process:

r\[n\] = √ Cc\[n − τ \]d\[n − τ \]s\[n − τ \]e j(2πνn+θ) + ω\[n\], (3)

where C is carrier power after front-end amplification, filtering, and quantization, c\[n − τ \] is ranging code chips shifted by an unknown delay τ , d\[n − τ \] is navigation message symbol, s\[n−τ \] is subcarrier modulation, ν is remaining frequency bias after down-conversion, θ is carrier phase, and ω\[n\] ∼ CN (0, σ2 ) is sample noise modelled as complex additive white Gaussian noise (AWGN) with variance σ 2 . Signal acquisition consists of generating a local Doppler shifted carrier, subcarrier, and ranging code replicas, correlating the input signal with the replicas using coherent and non-coherent stages, and a hypothesis testing to determine whether signal transmitted from a searched SV is present in the input. These steps are performed repeatedly for different candidate Doppler shift and code delay {ν ′ , τ ′} pairs using, e.g., grid-search until either the SV under search is found or all possible pairs are exhausted. Figure 7 illustrates signal acquisition using a block diagram.

1. Local replica generation and mixing involves the use of a candidate Doppler frequency ν ′ and front-end IF frequency to generate a waveform for compen sating remaining frequency bias in the input signal. Similarly, a subcarrier modulated ranging code replica is generated based on a candidate code delay


<!-- Page 30 -->

30

∑︁N−1 n=0 | · |2 ∑︁K−1 k=0

PRN code generator Subcarrier generator

Doppler NCO Doppler & Code delay search Continue search {τ ′ , ν ′} Search done Decision rule Coherent integration Non-coherent integration RC (τ ′ , ν′ ; k)

RNC (τ ′ , ν′ )

c\[n − τ ′ \] s\[n − τ ′ \]

e−j2πν′n r\[n\]

τ ′

τ ′

ν ′

Figure 7: Signal acquisition block diagram for detecting the presence of satellites and coarse estimation of signal Doppler shift and code delay \[8, p. 39\].

τ ′ the purpose of despreading the CDMA GNSS signal. The local replicas are mixed, i.e., multiplied, with input IF signal samples r\[n\] that are assumed here to follow the model defined in eq. (3).

2. To compute the correlation between the input signal and the local replicas, the now mixed signal is fed into an integrator which sums up a specified number N of samples over a coherent dwell time of TC = N/FS, where FS is the signal sample rate,

RC(τ ′ , ν′ ) = 1 N N ∑︂−1 n=0 c\[n − τ ′ \]s\[n − τ ′ \]e −j2πν′n r\[n\]. (4)

Result of (4) is referred to as a coherent integration result as it is obtained by summing in-phase and quadrature phase components separately. This captures both amplitude and phase information but, as a downside, performing coherent integration over a long period may lead to destructive interference due to phase unalignment caused by residual frequency error. This sets a limit for the maximum integration time that is dependent on the resolution of Doppler frequency estimates ν ′ . Destructive interference may also be caused by phase modulation of secondary codes or navigation message symbols d\[n\]. To address the issue of phase unalignment, the correlation period can be further extended using non-coherent integration methods. In non-coherent integration, phase information of coherent integration results obtained using (4) is discarded before summing the results together. Combining multiple shorter coherent integration periods non-coherently prevents phase unalignment but reduces signal-to-noise ratio (SNR) due to introduced noise magnitude bias. Non-coherent integration based on squared magnitude is defined as

RNC(τ ′ , ν′ ) = K ∑︂−1 k=0 |RC(τ ′ , ν′ ; k)| 2 , (5)


<!-- Page 31 -->

31

where k iterates over the K coherent integration bins of length N. It can be shown, as done in, e.g, \[65\], that the non-coherent integration result scaled by coherent integration noise variance σ 2 C ≈ σ 2/N follows a chi-squared distribution with 2K degrees of freedom when the SV under search is not present. It should be emphasised that the signal model in (3) does not include non-Gaussian noise terms from, e.g, interfering signals which would require additional consideration towards estimating the variance of coherent integration results. In the case that the searched SV is present, the scaled integration results follow a non-central chi-squared distribution with 2K degrees of freedom and a non-centrality parameter

λ(ν ′ , τ ′ ) ≈ CNK σ 2 sin2 (πN(ν − ν ′ ))

sin2 (π(ν − ν ′ )) R2 (τ − τ ′ ) R2 (0) , (6)

where R is the autocorrelation function of the subcarrier modulated ranging code. The formula also assumes that secondary codes or navigation message symbols do not cause destructive interference during coherent integration.

3. Detecting whether a signal from the searched SV is present and synchronized to generated local signal replicas involves the use of binary hypothesis testing. Respective distributions for non-coherent integration for a absent (H0) or a present (H1) SV can be modelled using (6) as

H0 : RNC(ν ′ , τ ′ )

σ 2 C ∼ χ 2 2K H1 : RNC(ν ′ , τ ′ )

σ 2 C ∼ χ ′2 2K(λ(ν ′ , τ ′ )), (7)

Figure 8 illustrates the distributions of √︂ RNC(τ ′ , ν′ ) under H0 and H1. A threshold value β splits the distributions into two regions corresponding to either accepting or rejecting the hypothesis H1. A detection, i.e. rejecting H0 when H1 is true, does not necessarily lead to successful signal tracking initialization if ν ′ and τ ′ are not within certain pull-in ranges from their true counterparts ν and τ . The ranges are defined by a receiver’s signal tracking architecture which defined the required grid-search resolution for acquisition. Neyman-Pearson lemma establishes the likelihood-ratio test as the uniformly most powerful test for perfectly modelled integration results. The test can be adapted to use a constant false alarm rate (CFAR) Pfa by adjusting detection threshold based on observed background or other grid-search {ν ′ , τ ′} cells. CFAR likelihood ratio test is defined as

Λ(τ ′ , ν′ ) = P(RNC(τ ′ , ν′ ) | σ 2 , C, ν, τ, H1) P(RNC(τ ′ , ν′ ) | σ 2 , H0) H1 ≷ H0 γ,

where threshold γ is adjusted such that P(Λ(τ ′ , ν′ ) > γ | H0) = Pfa.

The Neyman-Pearson lemma is only applicable in cases where the probability distributions under H0 and H1 are perfectly modelled, which requires the knowing of σ 2 , C, ν, and τ from distributions (7). As the parameters are not


<!-- Page 32 -->

32

readily available, they may instead be estimated from input signal using, e.g, maximum-likelihood (ML) estimation, which results in so-called generalized likelihood-ratio test (GLRT). In a GLRT method, any nuisance parameters are replaced by their ML estimates σˆ 2 , Pˆ , νˆ, and τˆ

ΛGLRT(τ ′ , ν′ ) = P(RNC(τ ′ , ν′ ) | σˆ 2 , Cˆ , νˆ, τˆ, H1) P(RNC(τ ′ , ν′ ) | σˆ 2 , H0) H1 ≷ H0 γ.

Since acquisition searches over multiple Doppler frequency and code delay {ν ′ , τ ′} pairs, there can be multiple true or false positives observed for a single SV. The positives can be tested further to eliminate the false alarms and to find the correct {ν ′ , τ ′} pair that matches the SV sent signal. Further testing can be accomplished by, e.g. repeating the acquisition process for the every positive {ν ′ , τ ′} cell in so-called multi-dwell detection. Ultimately, the goal of acquisition is to detect and successfully initialize tracking for a sufficient number GNSS signals over some minimum carrier-to-noise power density ratio. Acquisition parameter tuning of false alarm rate, coherent dwell time, number of non-coherent integration rounds, number of dwells, resolution of ν ′ and τ candidates, and signal detection probability may be used to balance receiver’s power usage, the number of acquired satellites, time needed to initialize tracking, and receiver design complexity.

H0: True negative H1: False negative H0: False positive (False alarm) H1: True positive (Detection)

H0 H1

0 √ β

Figure 8: Decision regions of √︂ RNC(τ ′ , ν′ ) under two hypotheses of SV not being

present H0 and SV being present H1. Detection threshold value is set at √ β.

3.3 GNSS signal tracking GNSS signal tracking refers to a process where time varying signal observables such as Doppler frequency, carrier phase, and ranging code phase are iteratively updated over time \[8, p. 57–66\] to maintain synchronization between an input and locally


<!-- Page 33 -->

33

generated signals. Like acquisition, signal tracking is based on correlating local signal replicas with input samples, but the methods differ in the sense that the tracking updates previously obtained observables to account for their slight changes over time. One tracking update is much less computationally intensive than acquisition, which is required for frequent observable updates. Tracking facilitates fine grade estimation of observables while accounting for satellite and receiver dynamics which cause constant variation in the received signal. Typically, GNSS signal tracking is based on repeatedly computing correlations between a received signal and local carrier and ranging code replicas in a recursive control feedback loop. For simplicity, the tracking loop is divided into separate carrier and code tracking stages, although the stages cannot function alone. Maintaining a good signal-to-noise ratio and obtaining new observable measurements requires existing coarse or fine grade synchronization of both the Doppler frequency and the code timing from either acquisition or previous tracking loop updates.

3.3.1 Carrier tracking loop

Carrier tracking involves compensating for changing Doppler frequency and main taining phase synchronization between a received signal and a local replica generated with a feedback controlled NCO \[8, p. 58–62\]. A signal used to tune the NCO is generated using a discriminator which outputs a value that is proportional to either the frequency or the phase error between the received and the local replica signals. The carrier tracking loop is referred to as either frequency-locked loop (FLL) or phase-locked loop (PLL) based on whether the discriminator measures frequency or phase error. Since a FLL is unable to correct for phase errors on its own, it has to be used in conjunction with a PLL. Frequency and phase discriminator functions operate on in-phase and quadrature phase correlation results between received and local replica signals \[14, p. 168\]. A maximum likelihood phase estimate is obtained by taking the argument of a complex correlation result, although different low-complexity discriminator alternatives exist as well. A phase discriminator can be used to define frequency discriminators by subtracting subsequent phase measurements and dividing the difference by the interval time between the measurement. Figure 9 shows a channel block diagram of an example carrier tracking loop. FLL and PLL discriminator outputs are filtered to reduce the effects of thermal noise and receiver clock phase jitter to maintain the stability of the feedback loop \[14, p. 179–193\]. Tracking loop filters are a common topic in GNSS research due to their importance on GNSS positioning and timing precision and maintaining receiver operation in different signal conditions. Tracking loop order determines the level of satellite and receiver dynamics the loop is able to compensate for. As an example, a third order PLL loop combined with a second order FLL loop allows satellite acceleration stress bias to be eliminated while still guaranteeing feedback loop stability \[14, p. 180\].


<!-- Page 34 -->

34

∑︁kNT n=(k−1)NT

Discriminator

Loop filter PRN code NCO Subcarrier generator

Carrier NCO Code tracking e−j(2πνˆn+θˆ) r\[n\]

ϵ FLL,PLL

˜ϵ FLL,PLL YP \[k\]

c\[n − τˆ\] s\[n − τˆ\]

Figure 9: Carrier tracking loop block diagram for a single tracking channel \[8, p. 59\].

3.3.2 Code tracking loop

A code tracking loop is used to synchronize the phase and the rate of a local replica ranging codes with a received signal \[8, p. 62–66\]. Observed code rate differs from its nominal value due to, e.g., Doppler effect and oscillator frequency biases. Code tracking is based on a delay-locked loop (DLL), where time shifted correlator outputs are compared in a discriminator to determine whether a local replica code is lacking or leading a received signal. Like with earlier FLL and PLL discriminators, DLL discriminator outputs are used to tune an NCO responsible for generating the local code replica and a subcarrier waveform. A loop filter is utilized to reduce discriminator noise. Figure 10 shows an example code tracking DLL loop based on a early–late design with three correlators. Early-minus-late (EML) discriminators compare correlation results from delayed or advanced ranging code replicas to estimate code phase offset between local and received codes \[8, p. 64–66\]. An EML discriminator can use one or more early and late correlators which are separated in time by an amount based on factors like input code frequency, the type of subcarrier modulation, and available front-end bandwidth. Higher frequency codes and subcarriers with narrower ACF peaks reduce the operational code timing window of a DLL and therefore require narrower early– late spacings. A DLL discriminator can also utilize a prompt correlator to normalize its outputs. A prompt correlator is synchronized to the input signal with zero code phase offset and is used for carrier tracking as well as estimating power and phase of the signal. Since satellite and receiver dynamics are common for both carrier and code tracking loops, a DLL may utilize carrier Doppler frequency measurements to precisely estimate code rate offset. This technique is referred to as carrier aiding and it effectively removes any code timing error due to the dynamics \[14, p. 162–164\]. Code rate offset ∆R can be calculated from measured carrier Doppler frequency as

∆R = ∆f/fcarr × Rc, (8)

where Rc is nominal code rate, fcarr is nominal carrier frequency, and ∆f is carrier Doppler frequency including any oscillator frequency bias. Carrier aiding allows for


<!-- Page 35 -->

35

reduced code tracking loop filter bandwidth, update rate, and filter order which can improve both precision and efficiency of the code tracking loop.

∑︁kNT n=(k−1)NT ∑︁kNT n=(k−1)NT ∑︁kNT n=(k−1)NT

Loop filter

PRN code NCO Subcarrier generation Carrier NCO

Carrier tracking r\[n\]

˜ϵ DLL ϵ DLL

c\[n − τˆ\] s\[n − τˆ\] e−j(2πνˆ\[k\]n+θˆ\[k\]) D/2 −D/2 Delay Delay YE\[k\]

YP \[k\]

YL\[k\]

Figure 10: Ranging code and subcarrier tracking loop block diagram for a single tracking channel. Early and late correlators are offset in time from a prompt correlator YP by ±D/2 \[8, p. 62\].

3.4 Demodulating and decoding navigation messages A receiver can begin to access navigation message symbols once its tracking loop channel has obtained a carrier phase lock to an input signal. Demodulating message symbols consists of wiping off Doppler frequency and correlating the signal with copies of subcarrier modulated ranging code over a single navigation message symbol period. This despreads the CDMA signal and gives access to the navigating message symbol encoded to the phase of the signal. The decoding process is in practice the same as obtaining a prompt correlator result already utilized for FLL, PLL, and DLL so no additional correlators must be implemented. A decision rule is used to decide whether an observed correlation result corresponds to either 0 or 1 sent from the tracked satellite. GNSS navigation messages employ various encoding techniques like error detection codes, forward-error-correction (FEC) coding, and interleaving as tools to mitigate disruptions in message communication. GNSS navigation message encoding and decoding processes are illustrated in figure 11. Depending on the receiver design, message decoders can be classified to either hard or soft decision decoders. The former operates on binary symbols obtained from a decision rule and the latter on soft decision symbols that include information on symbol uncertainty and applies a decision rule only after decoding. The advantage of soft decoders is the ability to assign weights to different symbols during FEC and focus on correcting the symbols with high uncertainty. 1. The goal of error detection is to indicate to a receiver whether a message has been received correctly. Error detection methods used in GNSS include


<!-- Page 36 -->

36

Transmission through atmosphere

Burst error protection

Error correction

Error detection Code and carrier synchronization

Deinterleaving

FEC decoding

CRC decoding

Message recovery

Receiver Code and carrier modulation

Interleaving

FEC encoding

CRC encoding

Message generation

Satellite

Figure 11: Navigation message encoding and decoding steps in a GNSS satellite and receiver.

Hamming codes and cyclic redundancy checks (CRC), with the latter being the more popular option. Error detection is based on additional redundancy bits included within sent messages. The redundancy bits are formulated according to the contents of the messages with, e.g., Hamming codes being parity check bits calculated for different subsets of message bits. In case a bit error was to occur, the information encoded into the redundancy bits no longer matches the contents, indicating that an error has occurred. There are various ways of constructing redundancy bits, which gives rise to different detection methods, such as Hamming codes and CRC. A commonly used CRC error detection method in GNSS is the Qualcomm 24-bit CRC (CRC-24Q) used by GPS, Galileo, and BDS \[10, 11, 48\]. The CRC is purely a detection scheme for erroneous messages and does not provide any tools to locate or correct bit errors. In a two-way communication system, failed CRC could be used induce a re-transmission of the erroneously received message. The communication link between GNSS space and user segments is however generally one-way but with repeating messages. A received message which fails a CRC check can therefore be discarded and a new message retrieval can be attempted some moments later.

2. Forward-error-correction (FEC) coding, also known as channel coding, consists of additional redundancy symbols added to a navigation message and a coding method which encodes the message’s information into the redundancy bits in a manner that allows possible bit errors to be corrected based on the received message alone. FEC methods are closely related to error detection schemes as,


<!-- Page 37 -->

37

by definition, error correction also requires error detection. However, effective correction requires far more redundancy bits than detection alone. The simplest FEC method is perhaps repetition codes where each message bit is transmitted multiple odd number of times. On the receiver side, a bit is allocated the value found on most of the received symbols associated with the bit. This way, as long as only a minority of the symbols are erroneous, the bit is received correctly. Modern FEC methods utilized in telecommunications are however more complex and far more powerful than repetition code. FEC methods used with GNSS include convolutional codes, BCH codes, Reed-Solomon codes, and low-density-parity-check (LDPC) codes \[11, 66\].

3. Message interleaving scrambles message symbols in a predictable way before transmission for the purpose of improving FEC performance. Message symbol errors appear commonly as bursts, where multiple consecutive symbols are flipped or set to a constant value. Deinterleaving done by a receiver scatters possible burst errors across the whole length of a message in a seemingly random order. This helps with error correction as FEC tends to be more effective against random noise rather than correlated bursts. Perhaps the simplest interleaving method is block interleaving, where a message of length NM is written into a N × M matrix row-wise, and then read column-wise to an interleaved message. The message is deinterleaved on the receiver side by column-wise writing and row-wise reading.

Navigation message symbol period varies between GNSS signals. GPS L1C has a symbol period of 10 ms and the symbols are synchronized with a 10 ms long ranging code. On the other hand, GPS L1 C/A has a symbol duration of 20 ms and a ranging code that spans only 1 ms. The C/A ranging code is therefore repeated 20 times for each symbol, and full utilization of the whole 20 ms duration in coherent correlation requires additional symbol level synchronization. Using the previously defined signal model in (3), prompt correlation results obtained from tracking can be written as

YP \[k\] = 1 Nd (k+1) ∑︂ Nd−1

n=kNd c\[n − τˆ\[k\]\]s\[n − τˆ\[k\]\]e −j(2πνˆ\[k\]n+ˆθ\[k\])r\[n\]

= √ C sin(πNd(ν − νˆ\[k\])) sin(π(ν − νˆ\[k\])) R(τ − τˆ\[k\]) R(0) e j(θ−ˆθ\[k\])d\[k\] + ωd\[k\]

= f(νˆ\[k\], τˆ\[k\], θˆ\[k\]) × d\[k\] + ωd\[k\] (9)

where ωd\[k\] ∼ CN (0, σ2/Nd) is complex additive white Gaussian noise. For a message symbol that lasts longer than a tracking loop update period, the correlators from (9) corresponding to the same symbol may be summed together.

R\[j\] = (j+1) ∑︂ Np+J−1

k=jNj+J YP \[k\], (10)

where J is offset obtained from symbol level synchronization.


<!-- Page 38 -->

38

Navigation message symbols included on the in-phase component of (10) are accessed by projecting the results onto the real axis

RI \[j\] = Re(R\[j\]) = (j+1) ∑︂ Np+J−1

k=jNj+J Re(f(νˆ\[k\], τˆ\[k\], θˆ\[k\]) × d\[k\] + ω\[j\]),

where ωI \[j\] ∼ N (0, σ2/2NdNj ). Symbols on the quadrature channel could be obtained similarly by projection on to the imaginary axis. Estimating the distribution of f(νˆ\[k\], τˆ\[k\], θˆ\[k\]) can be difficult in practice so approximate models based on signal tracking loop design, channel modelling, and estimation based on observed correlator outputs can be used when assessing soft decision symbol distribution in a soft decision decoder. For a hard decision decoder, or a signal without FEC, a simple decision rule for symbol can be defined as

d ˆ\[j\] = { 1 if RI \[j\] > 0 0 if RI \[j\] < 0 .

1 0 1 0

1 0 1 0

AWGN channel AWGN channel

Soft FEC Decision rule

Decision rule Hard FEC d\[j\] RNI \[j\] dˆ\[j\]

d\[j\] RNI \[j\] dˆ\[j\]

Figure 12: Navigation message receival and decoding based on hard (top) or soft (bottom) decoding. In the case a GNSS signal does not include interleaving, FEC, or CRC, the corresponding decoding blocks may be omitted.

3.5 Navigation solution computation As mentioned in section 2.1, GNSS position and timing solutions are based on pseu dorange measurements to multiple satellites ρ (p) indexed hereon using superscripts p = 0, 1, .... A pseudorange measurement is obtained by comparing time-of-arrival (TOA) and time-of-sending (TOS) of a signals from satellite p to the user as

ρ (p) = c(t (p) r − t (p) s ), (11)

where t (p) r is the signal TOA, and t (p) s is the signal TOS, and c is speed of light. The time difference is referred to as time-of-flight (TOF). At least four pseudorange measurement are needed from different satellites to solve for the receiver’s three

![page 38](images/image-004.png)

![page 38](images/image-005.png)

![page 38](images/image-006.png)

![page 38](images/image-007.png)

![page 38](images/image-008.png)

![page 38](images/image-009.png)

![page 38](images/image-010.png)

![page 38](images/image-011.png)


<!-- Page 39 -->

39

unknown position coordinates and clock bias between receiver clock and GNSS system time. A pseudorange measurement to a SV ρ (p) (x) from a user located x is modelled as

ρ (p) (x, ∆tu) = ||x − x (p) || + c(∆tu − ∆t (p) ) + I (p) + T (p) + ε (p) , (12)

where ||x−x (p) || is physical distance between the satellite and the user, ∆tu and ∆t (p) are user and SV clock biases in reference to GNSS system time, I (p) is ionospheric delay error, T (p) is tropospheric delay error, and ε (p) includes residual error terms. Components in ε (p) include, e.g., DLL timing jitter, multipath timing bias, and satellite ephemeris and clock errors, as well as plethora of small errors that may be neglected in code based positioning and timing. It should be noted that all of the parameters are time dependent but, for the sake of simpler notation, the time dependency is not explicitly written. Especially, the positions x and x (p) are not measured at the same instant, but instead at the signal’s sending and arrival times measured according to GNSS system time.

3.5.1 Satellite clock and group delay corrections

A GNSS navigation message contains reference time for the applicability of its included ephemeris information and clock correction parameters which are used to compensate for clock bias between the atomic clock of an broadcasting satellite and GNSS system time \[8, p. 74\]. All contemporary GNSS transmit their broadcast clock corrections as a set of three parameters af0, af0, af2 which are used to compute the satellite’s clock bias at time t as

∆t (p) = af0 + af1(t − t0e) + af2(t − t0e) 2 + ∆trel, (13)

where af0, af1, af2 are bias, drift and drift rate clock correction coefficients, t0c is a reference time for the coefficients, and ∆trel is a relativistic correction term defined as

∆trel = F e √ a sin(Et) = −2 √ µ c 2 e √ a sin(Et), (14)

where F = −2 √ µ/c2 = −4.442807633 × 1010 and Et is eccentric anomaly of the satellite. The eccentric anomaly is obtained when computing the satellite’s position as described in section 3.5.2. The relativistic correction accounts for time dilation between the SV clock situated on a MEO orbit and GNSS system time defined at Earth’s surface \[8, p. 74–75\]. For a perfectly circular orbit, the effect could be compensated for with a constant SV clock rate adjustment, but the slight ellipticity of GNSS orbits sets a requirement to include additional correction term that varies with the satellite’s movements. The difference in SV clock rate compared to GNSS system time is caused by the satellite’s relative speed and position in Earth’s gravity well compared to reference clocks situated on Earth’s surface. Satellite clock corrections are based on measurements taken by the system’s ground segment for dual-frequency ionosphere-free service. However, the instrumentation


<!-- Page 40 -->

40

delay of equipment on satellites is both frequency and code dependent and, therefore, additional correction parameters are issued through satellite broadcasts for single frequency and code users. These correction parameters are referred to using a few different terms like broadcast group delay (BGD), differential code bias (DCB), and inter-signal correction (ISC).

3.5.2 Computing satellite position using broadcast ephemeris

Broadcast ephemerides transmitted as parts of GNSS navigation messages contain information needed to estimate the near term orbital states of the system’s satellites. For GPS, the ephemerides are updated every two hours and include parameters to compute, e.g., in-orbit position and velocity of a transmitting satellite using Keplerian elements and correction parameters which account for orbital perturbations. Keplerian elements are a set of six parameters used to define a satellite’s position on an elliptical orbit. The parameters are illustrated in figure 13 and explained in the following list:

- Semi-major axis a of the orbit.

- Eccentricity e which defines the relationship between semi-major and semi-minor

axis of the orbit.

- Inclination i which is the angle between Earth’s equatorial plane and the orbit’s

plane.

- Right Ascension of the Ascending Node (RAAN) or longitude of ascending

node Ω which is the longitudinal angle between the vernal point and the orbit’s ascending node. Vernal point is defined as the direction at which Sun crosses the equatorial plane on March equinox and ascending node is the point at which the orbit crosses the equatorial plane northwards.

- Argument of the perigee ω which is the angle between the ascending node and

the perigee which is a point on the orbit closest to the Earth’s center of mass.

- True anomaly ν which is the angle between the perigee and the satellite as

seen from Earth’s center of mass.

GNSS broadcast ephemerides include the Keplerian parameters in a slightly modified format defined at an ephemeris reference time t0e. A receiver is able to predict the position of a satellite by extrapolating its anomaly forward in time using following calculations described in greater detail in, e.g., \[8, p. 73–74\]. The extrapolation is non-linear if true anomaly is used so a related parameter called mean anomaly is instead transmitted with the satellite’s ephemeris. Mean anomaly can be extrapolated linearly in time and transformed into true anomaly afterwards. True


<!-- Page 41 -->

41

i Ω ω ν

Ascending node Perigee

Vernal point N S

Figure 13: Six Keplerian parameters used to define the position of a satellite. Inclination i and RAAN Ω describe the orientation of an orbital plane while semi major axis a and eccentricity e define the shape of an orbit. Argument of perigee ω describes the orientation of the orbit on the plane and true anomaly ν defines the satellite’s position on the orbit.

anomaly νt at time t is computed as

Mt = M0 + √︃ µ a 3 (t − t0e)

Mt = Et − e sin(Et)

νt = 2 atan ( √︄ 1 + e 1 − e tan (︃Et 2 )︃ ) , (15)

where M0 is mean anomaly at a reference time t0e, Mt is mean anomaly at time t, µ is gravitational constant, Et is eccentric anomaly at time t. Et can be solved from the second equation using fixed-point iteration \[11\]. True anomaly at time t is summed with an argument of perigee ω to obtain an argument of latitude Φt

Φt = νt + ω.

A set of orbital corrections are applied to the argument of latitude Φt and a orbital radius rt = a(1 − e cos(Et)). The corrections account for, e.g., gravitational effects of third bodies like the Sun and the Moon, non-uniformity of Earth’s gravitational field, and solar radiation pressure. The corrected parameters are computed as

ut = Φt + Cus sin(2Φt) + Cuc cos(2Φt) rt = a(1 − e cos(Et)) + Crs sin(2Φt) + Crc cos(2Φt),

where Cus, Cuc, Crs, and Crc are harmonic argument and radius corrections included in the satellite’s broadcast ephemeris. Corrected parameters ut and rt are used to compute the satellite’s position on its orbital plane as

x ′ t = rt cos(ut) y ′ t = rt sin(ut). (16)


<!-- Page 42 -->

42

The position coordinates defined for the orbital plane need to be transformed into Earth-centered, Earth-fixed coordinate reference system such as WGS 84 for GPS satellites. This requires the orbit’s longitude of ascending node Ωt and inclination it . As ECEF is fixed to Earth’s rotation, the longitude of ascending node varies in time according to Earth’s speed of rotation. The two parameters used to compute the plane’s orientation are obtained as

Ωt = Ω0 + (Ω̇ − Ω̇ e)(t − t0e) − Ω̇ et0e it = i0 + i ̇(t − t0e) + Cis sin(2Φt) + Cic cos(2Φt),

where Ω0 is the reference longitude of ascending node, Ω̇ is the satellite’s rate of right ascension, Ω̇ e is Earth’s rate of rotation, and Cis and Cic are inclination correction coefficients. ECEF coordinates of the satellite are finally calculated from (16) as

xt = x ′ t cos(Ωt) − y ′ t cos(it) sin(Ωt) yt = x ′ t cos(Ωt) + y ′ t cos(it) cos(Ωt) zt = y ′ t sin(it). (17)

Due to the non-inertial nature of ECEF coordinates, signals between satellites and receivers do not propagate in straight lines and standard Euclidean distance can not easily be used to model pseudoranges. A simple method to account for this is to transform satellites’ ECEF coordinates to an Earth-centered inertial (ECI) coordinate system which coincides with the ECEF at a chosen reference time t0. Receiver position can be computed in the ECI and then transformed back into ECEF using a reverse transformation. A coordinate transformation from a ECEF to a ECI at time t is defined as a rotation around Earth’s axis of rotation as

\[ x ′ t y ′ t z ′ t \]

= \[ cos (︂ Ω̇ e(t − t0) )︂ − sin (︂ Ω̇ e(t − t0) )︂ 0

sin (︂ Ω̇ e(t − t0) )︂ cos (︂ Ω̇ e(t − t0) )︂ 0 0 0 1 \] \[ xt yt zt \]

,

where \[x ′ t , y′ t , z′ t \] T are the satellites coordinates in the ECI at time t.

3.5.3 Atmospheric pseudorange corrections

The pseudorange model considered in equation (12) includes errors from both iono spheric and tropospheric effects. The former are usually the more severe source of positioning and timing error for single-frequency receivers \[8, p. 80\]. The ionospheric effects are frequency dependent and vary in intensity depending on, e.g., solar activity, Earth’s magnetic field, receivers latitude, season, and time of day \[67\]. Ionospheric effects are modelled using total electron content (TEC) defined as the total number of electrons per square meter measured on a path from Earth’s surface to space. The ionospheric signal delay can be first order approximated as

I (p) (f) = 40.3 m3Hz2 /e − f 2 TEC(p) ,


<!-- Page 43 -->

43

where f is the carrier frequency of an signal and TEC(p) is total electron content usually given in total electron content units (TECU = 1016 e −/m2 ) \[8, p. 77\]. Dual-frequency receiver may exploit the frequency dependency of I (p) to accurately compensate for ionospheric error. However, for single-frequency receivers, such option is not available and instead correction parameters broadcasted from GNSS satellites or gathered from external sources have to be used. GPS broadcasts include eight Klobuchar model parameters αi , βii=0...3 for single frequency ionospheric corrections \[68\]. Klobuchar model uses a simplified geometry for the ionosphere in which electrons are assumed to be situated on a thin shell at around 350 km mean altitude above Earth’s surface. Ionospheric delay is estimated by finding a point at which a line of-sight ray from a satellite to a receiver antenna pierces the shell and computing a zenith ionospheric delay at the point. The satellite’s zenith angle is used to obtain a slant ionospheric delay that accounts for the satellite’s elevation. In general, different ionospheric models are applicable for all GNSS so, for example, corrections obtained from NeQuick-G model supported by Galileo can be used with GPS as well. Tropospheric delay accounts for pseudorange error originating from the lowest layers of the atmosphere \[8, p. 78\]. Unlike ionospheric delay, tropospheric delay does not depend heavily on a signal’s frequency, making its estimation based on tropospheric models and measurements relevant for both single- and multi-frequency users. Tropospheric delay can be split into two components referred to as hydrostatic, which accounts for dry gases, and wet, which accounts for water vapour and condensed water in the troposphere. Slant total tropospheric delay (STD) is defined based on these components as

STD = ZHD · mh(θ) + ZWD · mwv(θ), (18)

where ZHD and ZWD are zenith hydrostatic and wet tropospheric delays, and mh(θ) and mwv(θ) are hydrostatic and water vapour mapping functions which account for satellite’s zenith angle θ. Various models exist for both the zenith delays, e.g, Hopfield \[69\], Saastamoinen \[70\], and Mendes & Langley \[71\], and the mapping functions, e.g., Black & Eisner \[72\], Niell \[73\], and Vienna \[74\]. Exploring the advantages of and requirements for using the models goes outside the scope of the thesis.

3.5.4 Navigation solution solver

A receiver can begin to obtain navigation solutions after satellite positions and clock biases defined in (17) and (13) are available for at least four satellites. A navigation solution typically contains receiver position, velocity, and time (PVT) defined in the geodetic reference frame and system time of the utilized GNSS. Obtaining a navigation solution typically starts with coarse initial estimates for receiver position and GNSS system time although algorithms such as Bancroft’s method exist that do not necessitate any a priori information \[75\] on the receiver’s state. Initial position and time estimates can be based on, e.g., a previous navigation solution saved to receiver memory, internal receiver clock, or estimated based on observed satellites and approximate time-of-flight for signals travelling from MEO to Earth’s surface.


<!-- Page 44 -->

44

To obtain a positioning solution, the pseudorange measurement and model defined in (11) and (12) are combined with SV clock bias (13) and atmospheric delay corrections to a single equation

ρ (p) (x, b) = c(t (p) r − t (p) s ) = ||x − x (p) || + b + ε (p) , (19)

where t (p) r is measured signal TOA, t (p) s is known signal TOS, b = c∆t is receiver clock bias measured in meters, and ε (p) includes all residual errors. Solving the four unknowns from the non-linear equation (19) directly is difficult so iterative methods based on linearization, mainly Gauss-Newton and extended Kalman filter, are employed. The GPS L1C software receiver implemented in the thesis uses a Gauss-Newton algorithm that is described in detail in chapter 1.10 of a book GNSS Software Receivers \[8\]. To explain the algorithm in short, on each iteration, the receiver calculates errors for its current antenna position ∆xk and clock bias ∆bk estimates by solving a set of linearized pseudorange error equations written in matrix format as

∆ρk = \[ ∆ρ (1)(xk, bk) ∆ρ (2)(xk, bk)

. . . ∆ρ (N) (xk, bk) \]

= \[ xk−x (1) ||xk−x(1)|| , yk−y (1) ||xk−x(1)|| , zk−z (1) ||xk−x(1)|| , 1 xk−x (2) ||xk−x(2)|| , yk−y (2) ||xk−x(2)|| , zk−z (2) ||xk−x(2)|| , 1 . . . xk−x (N) ||xk−x(N) || , yk−y (N) ||xk−x(N) || , zk−z (N) ||xk−x(N) || , 1 \] \[ ∆xk ∆yk ∆zk ∆bk \]

= A \[︄ ∆xk ∆bk \]︄ ,

(20)

where ∆ρ (p) (xk, bk) = c(t (p) r − t (p) s ) − ρ (p) (xk, bk) are the differences between measured and modelled pseudoranges at the current estimate for receiver position and clock bias. The first three columns of the geometry matrix A contain unit vectors pointing from the receiver antenna to the tracked satellites. The set of linear equations in 20 is solved using ordinary least-squares as

\[︄ ∆xk ∆bk \]︄ = (ATA)−1A T∆ρk . (21)

On each algorithm iteration, the receiver position and clock bias estimates are updated based on the errors solved from (21)

xk = xk−1 + ∆xk−1, bk = bk−1 + ∆bk−1,

where k = 1, 2, ..., kmax with kmax being the maximum number of algorithm iterations. Around four iterations is typically sufficient for obtaining good position and time solution \[8, p. 81\].


<!-- Page 45 -->

45

### 4 GPS L1C Signal

GPS L1C signal consists of pilot and data channels transmitted on the L1-band at 1575.42 MHz central frequency with a reference bandwidth of 30.69 MHz \[11\]. The channels are transmitted in-phase with each other and the average chip delay between the channels’ ranging codes is guaranteed to not exceed 10 ns under nominal operating conditions. The two channels share most of their structures and include unique PRN ranging codes that allow the channels to be accessed at the same time. The pilot channel lacks a navigation message but includes instead a secondary PRN overlay code L1CO. The navigation message present on the L1C data channel is referred to as CNAV-2. The length and rate of an overlay code L1CO is equal to the length and symbol rate of a CNAV-2 message. The overlay code chip transitions are time synchronized with CNAV-2 symbol transitions. Unlike the earlier LNAV and CNAV messages utilized by GPS, CNAV-2 does not include a preamble word that is used to mark the beginning of every message or message subframe. Instead, the time synchronization between overlay codes and CNAV-2 messages is to be exploited when searching for navigation message epochs within a receiver \[16\]. As with other GPS signals, L1C navigation message, ranging codes, subcarriers, and carrier are generated coherently from a common 10.23 MHz clock source. This is highlighted in figure 14 which illustrates the overall GPS L1C signal structure.

L1CO 1800 chips 100 cps CNAV-2 1800 symbols 100 sps

10.23 MHz clock source PRN codes 10230 chips 1.023 Mcps L1CD

L1CP BOC(1,1) 1.023 MHz BOC(6,1) 6.138 MHz

Time-multiplexer

1575.42 MHz L1 carrier 1 2

√ 3 2

Figure 14: GPS L1C block diagram showing carrier, subcarriers, PRN codes, and CNAV-2 symbols generated coherently from a common 10.23 MHz clock source. Each 10230 chip primary code sequence spans one CNAV-2 symbol or L1CO chip. The transitions of CNAV-2 symbols and L1CO chips are time synchronized.

The minimum received terrestrial power of combined GPS L1C data and pilot channels at the 30.69 MHz reference bandwidth is −157 dB W. The minimum power is around 1.5 dB higher than for the L1 C/A or L2C broadcasted by GPS Block III satellites \[11, 28\]. The carrier power of L1C is not distributed equally between its channels as 75% of it is dedicated for the pilot and the rest 25% for the data. Like other GNSS signals, GPS L1C is transmitted as right-handed circularly polarized (RHCP). If considering only the −158.25 dB W minimum received power of L1C pilot


<!-- Page 46 -->

46

channel, the new GPS signal provides slightly more resilience against interference and receiver noise than L1 C/A or L2C. Table 9 summarizes the GPS L1C signal definition. The generation of GPS L1C PRN codes, TMBOC subcarrier modulation, and CNAV-2 channel encoding are presented in the following sections to provide the necessary definitions needed to implement a functioning GPS L1C receiver.

Signal GPS L1C Frequency Band L1 Center frequency 1575.42 MHz Multi-access technique CDMA PRN code families Weil code & M-sequence/Gold code Primary PRN code length 10230 PRN code frequency 1.023 MHz Signal component Data Pilot Secondary code - 1800 chips at 100 cps Data rate 50 bps at 100 sps - Subcarrier modulation BOC(1,1) BOC(1,1) & BOC(6,1) Subcarrier frequency 1.023 MHz 1.023 MHz & 6.138 MHz Minimum received power -163 dBW -158.25 dBW Joint minimum recv. power -157 dBW

Table 9: Listed GPS L1C signal specifications from IS-GPS-800J ICD \[11\].

4.1 GPS L1C ranging and overlay codes GPS L1C signal includes three different PRN codes: pilot L1CP, data L1CD, and overlay L1CO \[11\]. The first two are the primary ranging codes of L1C pilot and data channels respectively. The two codes are generated by expanding 10223 bit long Weil sequences with 7 expansion bits, meaning that the total length of either code is 10230 chips. Weil sequences generated for different SVs are unique and have a very small cross-correlation to facilitate DS-CDMA. The chipping rate of the codes is 1.023 Mcps and each code therefore spans 10 ms in time. The delay between chip transitions of L1CP and L1CD transmitted from the same SV can be assumed to be below 10 ns and below 1 ns with 95% probability \[11\]. The overlay codes L1CO are 1800 bit long secondary PRN sequences added to GPS L1C pilot channels. An overlay code is generated coherently with L1C data channel CNAV-2 navigation message and its length matches that of the CNAV-2 \[11\]. The overlay code provides navigation message synchronization and modulation-free pilot channel tracking as the chips of the code can be predicted after initial code synchronization is obtained. The latter helps in signal tracking as coherent phase discriminators can be utilized in the absence of unknown phase modulation. Together, the overlay code L1CO and the pilot channel ranging code L1CP form a tiered code


<!-- Page 47 -->

47

with a much longer non-repeating length than L1CP alone. The secondary code also improves narrowband interference suppression by decreasing spectral lines \[16\].

4.1.1 Generating GPS L1C ranging codes

GPS L1C primary ranging codes are defined using Weil sequences which are pseudo random sequences of prime integer length \[11\]. In case of L1CP and L1CD, the length is 10223. A Weil sequence Wi for a GPS SV with PRN number i ∈ {1, ..., 210} is created from a Legendre sequence L\[t\] where t ∈ {0, ..., 10222} defined as L\[0\] = 0 L\[t\] = 1, if there exists an integer x such that t is congruent to x 2 mod 10223

L\[t\] = 0, if there exists no integer x such that t is congruent to x 2 mod 10223.

A Weil sequence Wi \[t\] is defined from L\[t\] as

Wi \[t\] = L\[t\] ⊕ L\[(t + wi) mod 10223\] for t ∈ {0, ..., 10222},

where wi is an unique Weil index of the SV with PRN i. The index differs between the data and pilot channels of the same SV. The generated Weil code is expanded to a desired length of 10230 chips by inserting a seven chip-long expansion sequence E\[t\] = \[0, 1, 1, 0, 1, 0, 0\] to a predetermined place in the code as

L1CDi \[t\]/L1CPi \[t\] = { Wi \[t\] for t = 0, ..., pi − 2 E\[t − pi − 1\] for t = pi − 1, ..., pi + 5 Wi \[t − 7\] for t = pi + 6, ..., 10229,

where pi is an unique insertion index for the SV with PRN number i. Like wi , the insertion index pi differs between the data and pilot channels. Parameters wi and pi are given for all GPS satellites and both signal channels in IS-GPS-800 interface control document (ICD) \[11\].

4.1.2 Generating GPS L1C overlay codes

A GPS L1C overlay code L1CO is defined using one or two truncated M-sequences. A M-sequence of length 2 11 − 1 = 2047 is generated using a 11-stage linear-feedback shift register (LFSR) and then truncated to a desired length of 1800 symbols. For GPS SVs with PRN numbers between 1 and 63, which includes all of the current GPS satellites in space, only a single M-sequence is used. GPS documentation supports PRN numbers up to 210, and for PRN 64-210, the overlay codes are defined instead as truncated Gold codes. A truncated Gold code is generated by modulo-2 addition of two truncated M-sequences. Figure 15 showcases the operation of a 11-stage LFSR. On each cycle, the symbol n11 is picked as a new LSB of an output M-sequence. The first symbol of the next LFSR stage is generated using modulo-2 sum n ′ 1 = ( ∑︁11 j=1 mjnj ) mod 2, where mj ∈ {0, 1} are coefficients of a SV specific generator polynomial. The symbols are shifted to the right to generate the next LFSR stage as n ′ j = nj−1 where j ∈ {2, ..., 11}. Generator polynomials and initial LFSR stages are given for all GPS SV PRN numbers in IS-GPS-800 ICD \[11\].


<!-- Page 48 -->

48

Output

0 1 2 3 4 5 6 7 8 9 10 11 n1 n2 n3 n4 n5 n6 n7 n8 n9 n10 n11 m1 m2 m3 m4 m5 m6 m7 m8 m9 m10 m11

Figure 15: 11-stage linear-feedback shift register used to generate M-sequences for GPS L1C overlay codes \[11\]. Coefficients mi where i = 1, ..., 11 are defined by a primitive generator polynomial.

4.2 TMBOC subcarrier modulation GPS L1C data and pilot channel ranging codes are modulated using both BOC(1,1) and BOC(6,1) binary offset carriers following a sinBOC definition \[11\]. The data channel modulation is pure BOC(1,1) while the pilot channel is modulated using time-multiplexed BOC(1,1) and BOC(6,1). The combined data and pilot channel modulation scheme is referred to as time-multiplexed BOC or TMBOC(6,1,1/11) and it is the GPS version of MBOC(6,1,1/11) modulation also adopted by Galileo E1 OS, QZSS L1C, and BDS B1C. The PSDs of the different realizations of MBOC(6,1,1/11) are equivalent while their time-domain implementations vary based on designs adopted for the respective systems. The number 1/11 refers to the fact that 1/11 of the transmitted power is modulated with BOC(6,1) and the rest with BOC(1,1). BOC(1,1) can work as a decent approximation for modulating local signal replicas of both the L1C channels as the subcarrier constitutes 100% of the data channel and 1 − 4/33 ≈ 88% of the pilot channel power. Spectral side peaks of BOC(1,1) are also closer to the L1C center frequency than BOC(6,1) meaning that the former component can be tracked using a lower front-end bandwidth and sampling rate. The whole pilot channel subcarrier modulation is referred to as TMBOC(6,1,4/33). The time-domain implementation of GPS L1C subcarrier is illustrated in figure 16 and figure 17 shows the autocorrelation functions of infinite bandwidth BOC(1,1), TMBOC(6,1,4/33), and TMBOC(6,1,1/11) subcarriers. A sharper autocorrelation peak supports less noisy code timing and pseudorange estimation.

4.3 CNAV-2 navigation message A GPS L1C data channel carries navigational data in CNAV-2 navigation message format \[11\]. Each CNAV-2 message is 1800 symbols long and spans 18 seconds in time. The format consists of three subframes as illustrated in figure 18:

- Subframe 1 includes time of interval (TOI) data. Eight least-significant bits

(LSB) of a TOI are channel encoded using BCH(51,8) method with a generator polynomial of 763 (octal) \[11\]. Ninth and the most significant bit (MSB) of the TOI data is then added modulo-2 to each of the 51 BCH encoded symbols and prepended into the sequence forming a 52-symbol encoded TOI message. TOI data counts the number of 18-second CNAV-2 messages since the start of


<!-- Page 49 -->

49

(a) Data

(b) Pilot BOC(1,1)

L1CD

BOC(1,1) & BOC(6,1)

L1CP 0 1

0 1

0 1

0 1 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32

0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 Figure 16: TMBOC modulation applied to GPS L1C data (a) and pilot (b) channels shown for 33 chip-long sequence. Data channel modulation is pure BOC(1,1) while a pilot component has both BOC(1,1) and BOC(6,1) modulations which are time multiplexed such that chips numbered 0 + 33t, 4 + 33t, 6 + 33t and 29 + 33t, where t = 0, ..., 309 of a 10230 chip long ranging code out are modulated using BOC(6,1) and the rest using BOC(1,1). The time-multiplexed BOC sequence is repeated every 33 ranging code chips so only a single period is illustrated.

the latest two-hour period represented by interval time of week (ITOW) count given in subframe 2.

- Subframe 2 includes 576 bits of time, clock correction, and ephemeris data

with an added 24 bit long CRC-24Q redundancy check \[11\]. The 600 bit long message is channel encoded using 1/2 LDPC encoder with 600 by 1200 sparse parity check matrix H2 given in ICD \[11\]. A block interleaver of size 38 × 46 is also applied to subframes 2 and 3 jointly to further protect the message against burst errors. The contents of the subframe 2 stay nominally the same during a 2-hour transmission interval, which can be utilized in low SNR conditions where decoding over a single message fails. In such situation, each symbol of the encoded subframe 2 could be estimated as, e.g., the corresponding symbol found in a majority of multiple received messages.

- Subframe 3 includes varying additional data like satellite almanac, ionospheric

correction parameters, differential corrections, SV configuration and integrity support message \[11\]. The CNAV-2 message format does not include all of this data in a single navigation message, but rather has a dedicated page for each type. Only a single page is transmitted as part of one CNAV-2 message with the page type identified by a six bit long page number provided in bits 9 to 14 of subframe 3. The page sent is varied between messages and decidedly doesn’t follow a predetermined sequence. Currently, the GPS L1C ICD defines the structure for page types numbered from 1 to 8 \[11\].


<!-- Page 50 -->

50

−1 −0.8 −0.6 −0.4 −0.2 0 0.2 0.4 0.6 0.8 1 −0.5 0 0.5 1

Code delay \[chips\]

Data BOC(1,1) Pilot BOC(1,1) Both BOC(1,1) Pilot TMBOC(6,1,4/33) Both TMBOC(6,1,1/11)

Figure 17: Autocorrelation functions for infinite bandwidth BOC(1,1), TM BOC(6,1,4/33), and TMBOC(6,1,1/11) subcarrier modulations scaled by their nor malized power in GPS L1C signal.

Similarly to the subframe 2, subframe 3 has an additional CRC-24Q appended to its page data. The total subframe 3 length is 274 bits which is encoded into a 548 symbol long message using 274 by 548 sparse parity check matrix H3 given in ICD \[11\]. Again, a block interleaver of size 38 × 46 is applied to subframes 2 and 3 jointly to form the latter part of a CNAV-2 message.

Subframe 1 Subframe 2 Subframe 3 Time of interval Clock & ephemeris Variable data 9 Bits 576 Bits + 24 Bit CRC 250 Bits + 24 Bit CRC

BCH(51,8) encode ½ LDPC encode ½ LDPC encode

38 × 46 Block interleave

CNAV-2 Message 1800 symbols transmitted at 100 sps for 18 seconds

Figure 18: CNAV-2 navigation message encoding diagram \[11\].


<!-- Page 51 -->

51

### 5 GPS L1C Receiver Implementation

A GPS L1C receiver was implemented in the thesis for the FGI-GSRx GNSS software receiver developed at Finnish Geospatial Research Institute. The receiver comprises various signal processing modules implemented as MATLAB functions. Main four modules of the receiver are signal acquisition, signal tracking, navigation message decoding, and position, velocity, and timing (PVT) computation. The modules are executed in a pipeline fashion in the listed order. The L1C receiver was programmed for FGI-GSRx by adapting the four modules of the receiver to be GPS L1C compatible. Acquisition and tracking modules required the generation of local L1C replica signals based on the ranging code and TMBOC modulation definitions explained in the previous chapter. CNAV-2 decoding was implemented from scratch due to the completely new navigation message definition. The implemented GPS L1C receiver PVT computation module required practically no changes from the existing FGI GSRx implementation except for how CNAV-2 message epochs were calculated from message data for determining signal time-of-sending. Figure 19 illustrates the FGI-GSRx GPS L1C receiver processing chain. The receiver post-processes raw signal I/Q-samples from an input file into usable signal observables and PVT solutions. Once a module has been executed, the receiver no longer returns to that module during the same run. This means that, e.g., the receiver does not attempt to reacquire signals that have been lost by the tracking module. The modules generate outputs that cover the entire processing period such that, e.g., signal tracking channels for different SVs save their signal observables over the defined processing time into a MATLAB data structures. The saved data is then utilized by the latter CNAV-2 decoding and PVT computation modules to produce the final GPS L1C PVT solutions.

Antenna

RF front end

GNSS simulator File Tracking

Acquisition PVT computation

CNAV-2 decoding PVT solution

Coarse Doppler & code phase estimates Data channel correlator Ephemerides, & clock information Raw I/Q samples Fine code phase estimates

Figure 19: FGI-GSRx module diagram for the GPS L1C receiver implementation. The receiver processes raw I/Q-files obtained using an RF front end or a GNSS simulator and outputs observables, such as code phase estimates, and PVT solutions for receiver antenna location and GPS system time.


<!-- Page 52 -->

52

### 5.1 GPS L1C signal model

A sampled GPS L1C signal was modelled for the implementation using pilot and data channel signal structures and additive white Gaussian noise (AWGN)

r\[n\] = ( √︄ 3C 4 × cP \[n − τ \] × cO\[n − τ \] × sP \[n − τ \]

+ √︄ C 4 × cD\[n − τ \] × d\[n − τ \] × sD\[n − τ \] ) e j(2πνn+θ) + ω\[n\], (22)

where n is sample index, C is total carrier power, τ is code delay, ν is carrier frequency offset after down-conversion, θ is carrier phase, cP and cD are the pilot and data channel primary ranging codes, cO is an overlay code chip, d is a CNAV-2 message symbol, sP and sD are the pilot and data channel components of TMBOC(6,1,1/11) subcarrier, and ω is complex AWGN with variance σ 2 .

### 5.2 Signal acquisition

The signal acquisition module in FGI-GSRx receiver uses a fully parallel grid-search approach where non-coherent integration results defined in formula (26) are calculated for all candidate frequency offset ν ′ and code delay τ ′ pairs referred to as grid-search cells. Afterwards, a binary hypothesis test statistic is computed only for the highest observed result. The fully parallel acquisition approach takes advantage of convolution theorem and discrete Fourier transform (DFT) implemented through fast Fourier transform (FFT) to efficiently compute correlation results over all of the grid-search cells. Coherent integration results are computed in the frequency domain simultaneously for a candidate frequency offset ν ′ and all candidate code delay values at the resolution of one sample. First, the DFT of a TMBOC modulated GPS L1C ranging code replica for a searched SV is computed as

C\[m\] = ∑︂ N

n=1 c\[n\]s\[n\]e −j2πmn/N , (23)

where c\[n\] and s\[n\] are local replicas of satellite’s PRN code and subcarrier modulation resampled to match the sampling rate FS of an input signal r\[kNd + n\] assumed to follow equation (22). The number of samples N in one coherent integration dwell is equal to the code period Tc of 10 ms times sample rate FS. The input signal is mixed with a complex sinusoid of frequency ν ′ and discrete Fourier transformed as

r ′ ν ′\[n\] = r\[kNd + n\]e −j2πν′n , R ′ ν ′\[m\] = N ∑︂−1 n=0 r ′ ν ′\[n\]e −j2πmn/N . (24)

Coherent correlation results for all candidate code delay values are obtained simulta neously by taking inverse DFT from the product between the local code replica in


<!-- Page 53 -->

53

(23) and mixed input signal in (24) as

RC(ν ′ , τ ′ ) = r ′ ν ′\[τ ′ \] ∗ c ∗ \[−τ ′ \] = 1 N N ∑︂−1 m=0 R ′ ν ′\[m\]C ∗ \[m\]e j2πmτ′/N . (25)

The coherent integration process is repeated K ≥ 1 number of times for subsequent bins of input data and the results summed together using (26) to produce the final non-coherent integration results as

RNC(τ ′ , ν′ ) = K ∑︂−1 k=0 ⃓ ⃓ ⃓R (k) C (τ ′ , ν′ ) ⃓ ⃓ ⃓ , (26)

where k indexes the coherent integration bins. Obtained non-coherent integration results are stored to a column of an array of size Nτ × Nν, where Nτ is the number of searched code delay values and Nν is the number of searched Doppler frequencies. The process is repeated for all grid-search cells until the entire array has been filled. After the correlation computations, a signal detection test statistic is computed for the highest observed non-coherent integration result. The candidate parameters τ ′ and ν ′ matching the highest correlation result are picked as the coarse estimates for signal frequency offset and code timing delay.

τˆ, νˆ = arg max {ν ′ ,τ′} RNC(ν ′ , τ ′ ). (27)

The detection of GPS L1C signals within the input samples is based on a simple noise ratio test defined for the cell under test {τˆ, νˆ} as

RNC(τˆ, νˆ) − µNC σNC H1 ≷ H0 γ, (28)

where γ is an user defined detection threshold and µNC and σ are the mean and the standard deviation for background non-coherent integration results. The results used to compute µNC and σ include all of the grid-search cells with the Doppler frequency νˆ and code delays that are offset from νˆ by at least one code chip. The offset avoids the sampling of signal ACF peak when estimating background mean and standard deviation. It should be noted that the defined noise ratio test does not produce optimal receiver operating characteristics as the non-coherent integration results are known to be non-Gaussian. The choice for the test statistic offers a simple yet sufficient solution for most applications of the receiver. The presence of SVs within a research setting is typically known, which allows a user to tune the acquisition module such that correct detections are obtained and false alerts are avoided. The most important part of finding coarse estimates for Doppler frequency ν and code delay τ needed to initialize signal tracking is accomplished if the correlation result produced by the signal is higher than the other results produced from background noise. GPS L1C acquisition can be based on either one or both of the signal’s channels. Two options were implemented for the L1C receiver of this thesis: pilot only acquisition


<!-- Page 54 -->

54

and combined channel acquisition. In the latter, coherent correlation results were calculated separately for both data and pilot channels using (25) after which weighted sum and difference of the results were computed as in (29). Number K ≥ 1 of integration results could be added semi-coherently following equation (30) such that on each round either the weighted sum or the weighted difference was added depending on which of the values had the greater magnitude. For reference, semi-coherent integration based on squared magnitudes had been explored previously in, e.g., \[65, ch. 7.3.3\]. Weighted sum and difference between pilot and data channels were computed as

RC+(ν ′ , τ ′ ; a) = a × RC,pilot(ν ′ , τ ′ ) + (1 − a) × RC,data(ν ′ , τ ′ ) RC−(ν ′ , τ ′ ; a) = a × RC,pilot(ν ′ , τ ′ ) − (1 − a) × RC,data(ν ′ , τ ′ ), (29)

where a ∈ \[0, 1\] is pilot channel weighting, and semi-coherent integration result as

RNC(ν ′ , τ ′ ; a) = K ∑︂−1 k=0 max (︂ |R (k) C+(ν ′ , τ ′ ; a)|, |R (k) C−(ν ′ , τ ′ ; a)| )︂ , (30)

where k indexes the coherent correlation bins. After (30) had been computed for each grid-search cell, the results were tested using (27) and (28) just like in pilot-only acquisition. Coefficient a was obtained by assuming that the coherent correlation results for the two channels are normally distributed and independent of each other. Figure 20 shows normalized SNR as a function of a with the optimal value aopt being obtained as

aopt = arg max a (︄ mean(RC+/−(ν ′ , τ ′ ; a) var(RC+/−(ν ′ , τ ′ ; a)) )︄ = √ 3 1 + √ 3 .

0 0.25 0.5 aopt 0.75 1.0 0 0.25 0.5 0.75 1

a

Figure 20: Normalized SNR of combined correlation results for GPS L1C pilot and data channels as a function of weighting parameter a.


<!-- Page 55 -->

55

### 5.3 Signal tracking

Signal tracking in FGI-GSRx utilizes a combination of frequency-locked (FLL) and phase-locked (PLL) loops for carrier tracking and a delay-locked loop (DLL) for code tracking. The loops operate at a constant update rate of 1 kHz and on each iteration Nd = 1 ms × Fs input samples are coherently correlated with local replicas generated by carrier and code NCOs. The correlations results are used to estimate offset between input and local replica signals and the offset tunes the NCOs in a feedback control loop. Each tracked GPS SV is assigned an individual tracking channel that are updated one by one on each tracking loop update. Carrier NCO phase θ ∈ \[0, 2π\[ in radians as a function of input sample number kNd + n where n ∈ \[0, Nd − 1\] is computed from equation (31) as

θ ˆ\[kNd + n\] = 2π (νIF + νacq + ∆ν\[k\]) n FS + θ\[kNd\] mod 2π, (31)

where νIF is front end IF frequency, νacq is frequency bias set to the acquired Doppler frequency, and ∆ν\[k\] is filtered carrier error from FLL and PLL discriminators. The frequency error and carrier phase are initialized to zeros at the beginning of tracking. Code NCO phase τ ∈ \[0, 10230\[ measured in chips is computed similarly as

τˆ\[kNd + n\] = (︄(︄ 1 + ν\[k\] fcarr )︄ fc + ∆fc\[k\] )︄ n FS + τ \[kNd\] mod 10230, (32)

where ν\[k\] = νacq + ∆ν\[k\] is tracked carrier Doppler frequency, fcarr = 1575.42 MHz is nominal L1 carrier frequency, fc = 1.023 MHz is code chipping rate, and ∆fc is filtered code error from DLL discriminator. The aiding provided by the carrier Doppler estimate effectively compensates for any code dynamics and makes thermal noise the singular dominant source of code timing jitter. Local signal replicas are used on each loop iteration k to compute prompt corre lation results from input samples as

IP \[k\] + jQP \[k\] = N ∑︂d−1 n=0 cP (τˆ\[kNd + n\])sP (τˆ\[kNd + n\])e −jθˆ\[kNd+n\] r\[kNd + n\], (33)

where cP and sP are L1C pilot code and subcarrier as a function of code phase and r is input sample. The receiver also computes early (IE + jQE), late (IL + jQL), and very early (IEE + jQEE) correlation results using equation (33) but with τˆ\[kNd + n\] offset in time by D/2 for the early, −D/2 for the late, and δEE = 2 chips for the very early correlator. In-phase data channel prompt correlator IP,data is also computed using (33) by replacing the pilot channel code cP and subcarrier sP with data channel equivalents. The data correlator outputs were not utilized in the GPS L1C receiver implementation for signal tracking but were needed for accessing CNAV-2 symbols later during decoding. The very early correlator is used to estimate channel noise power for determining signal carrier-to-noise density ratio (C/N0). The very early correlator offset δEE was set two primary code chips earlier than the prompt correlator to guarantee that


<!-- Page 56 -->

56

only noise power is sampled. An early correlator is preferred over a late one to avoid multipath replicas that appear on the delayed side of the correlation peak \[76\]. Estimates for prompt correlator power Cn, noise power N, and C/N0 were computed from prompt and very early correlators as

Cn\[k\] = 1 M M ∑︂−1 m=0 (︂ IP \[k − m\] 2 + QP \[k − m\] 2 )︂ ,

N\[k\] = 1 M M ∑︂−1 m=0 (︂ IEE\[k − m\] 2 + QEE\[k − m\] 2 )︂ , (34)

C/N0\[k\] = 10 × log10 (︄ Cn\[k\] − N\[k\] N\[k\] × 1 Tcor )︄ , (35)

where Tcor = 1 ms is the tracking loop correlation period. With M = 1000 and Tcor = 1 ms, the moving average in the estimation was computed over a one second window.

5.3.1 Carrier tracking loop discriminator

A carrier tracking loop is used to control an NCO to match the frequency and the phase of local carrier replicas to an input signal affected by Doppler’s effect. The carrier tracking combines a FLL and a PLL to produce the desired NCO control signal. The implemented FLL and PLL measured frequency and phase error using inverse tangent discriminators defined as

ϵ FLL\[k\] = 1 2πTcorFS atan (︄ IP \[k − 1\]QP \[k\] − IP \[k\]QP \[k − 1\] IP \[k\]IP \[k − 1\] + QP \[k\]QP \[k − 1\] )︄ , (36)

ϵ PLL\[k\] = 1 2π atan (︄ QP \[k\] IP \[k\] )︄ , (37)

where Tcor = 1 ms is the tracking loop update interval, FS is input sampling rate, and IP and QP are in-phase and quadrature phase components of prompt correlator results. Both of the chosen discriminators were invariant to 180◦ phase shifts present on the pilot channel due to unsynchronized GPS L1C overlay codes. Figure 21 illustrates the discriminator outputs as a function of frequency and phase errors. The frequency discriminator of equation (36) works by comparing the phases of subsequent prompt correlator results. As the time interval between the phase measurements is known, the difference can be divided by the interval to obtain an estimate for the instantaneous frequency error. The frequency discriminator can be viewed as a backward difference approximation for the derivative of the signal’s phase.


<!-- Page 57 -->

57

−1 −0.5 0 0.5 1 −0.4 −0.2 0 0.2 0.4

(a) Normalized frequency error δf/FS −2 0 2 −0.4 −0.2 0 0.2 0.4

(b) Phase error δθ \[rad\]

Figure 21: Frequency error vs. FLL discriminator in (36) (a) and phase error vs. PLL discriminator in (37) (b) for noise-free infinite bandwidth signals.

5.3.2 Code tracking loop discriminator

The ranging code of GPS L1C pilot channel is tracked using a delay-locked loop. The chosen loop discriminator function for the L1C receiver implementation was so-called normalized non-coherent early-minus-late discriminator (NNEML) defined as

ϵ DLL NNEML\[k\] = (︄ 1 |k| − D 2 )︄ √︂ I 2 E\[k\] + Q2 E\[k\] − √︂ I 2 L \[k\] + Q2 L \[k\] √︂ I 2 E\[k\] + Q2 E\[k\] + √︂ I 2 L \[k\] + Q2 L \[k\] , (38)

where k is the slope of a signal’s normalized autocorrelation function (see 17) around its main peak and D is the early-late correlator spacing \[8, p.65\]. Scaling in equation (38) was chosen such that there is an one-to-one correspon dence between the discriminator output and signal code phase error for infinite bandwidth GPS L1C signals. The width of the linear one-to-one region is dependent on the width of the center peaks of BOC(1,1) or TMBOC(6,1,4/33) autocorrelation functions and the choice of early-late spacing D. The maximum width DLL linear region is obtained at D = 1/3 chips for BOC(1,1) and D = 1/12 chips for TMBOC(6,1,4/33). Using lower values for D improves code tracking precision at the cost of narrowing the linear region. The minimum useful value for D can be calculated as fc/Bfe, where fc is code chipping rate and Bfe is front-end bandwidth \[77\]. The absolute values for the slopes k for the two modulations were approximated from infinite bandwidth ACF as |k| = 3 per chip for BOC(1,1) and |k| = (29 × 3 + 4 × 23)/33 = 179/33 per chip for TMBOC(6,1,4/33). The NNEML discriminator is insensitive to phase variations of the input signal as it uses magnitudes of the early and late correlators. This comes at the cost of increased noise and non-linearity that ultimately reduce code timing precision. Similar NNEML discriminators have been used within FGI-GSRx to track other GNSS signals, for which the discriminator has been found to be effective. Figure 22 illustrates the NNEML discriminator output as a function of code delay error. The width of the linear region for the TMBOC modulated signal in the figure is one fourth of the width of the linear region for the BOC modulated signal.


<!-- Page 58 -->

58

−1 −0.8 −0.6 −0.4 −0.2 0 0.2 0.4 0.6 0.8 1 −0.2 −0.1 0 0.1 0.2

Code phase error τ − τˆ \[chips\]

BOC(1,1): D = 1/3 chips, |k| = 3 per chip TMBOC(6,1,4/33): D = 1/12 chips, |k| = 179/33 per chip

Figure 22: NNEML discriminator output as a function of code phase error of equation (38) for noise-free infinite bandwidth BOC(1,1) and TMBOC(6,1,4/33) signals.

5.3.3 Tracking loop filters

The tracking loop filters reduce the impact of noise on carrier and ranging code discriminator outputs. The filters used in FGI-GSRx are described in detail in a paper on the receiver design \[78\]. In short, the FLL, PLL, and DLL all employ second order loop filters. Loop filter parameters, those being filter bandwidth, control loop gain, and damping ratio, can be manually tuned using a receiver configuration file before processing. Filter parameters used for testing the GPS L1C implementation are described in a later thesis chapter 6 addressing the receiver setup. The implemented GPS L1C tracking uses a three-stage carrier tracking design where FLL and PLL filter bandwidths are varied based on the stability of carrier frequency and phase estimates. The three stages are: pull in, coarse tracking, and fine tracking. Initially, pull in mode is used where FLL and PLL loop filter bandwidths are kept large to allow for the quick convergence of frequency offset remaining from acquisition and initially unsynchronized carrier phase. As the tracking loops become locked on to the input signal, the filter bandwidths are decreased to further reduce the impact of noise on carrier frequency and phase estimates. Code timing precision of the GPS L1C receiver can be predicted based on theoretical models for NNEML discriminator timing jitter. The timing jitter is dominated by thermal noise and dynamic stress error from high order satellite and receiver dynamics. The latter error is negated effectively using a carrier aided code tracking loop. The remaining jitter for a non-coherent DLL discriminator due to thermal noise can be estimated numerically from equation (39). The equation was utilized for comparing precision of the implemented L1C receiver to theoretical expectations as explained in thesis’s results section 7.4.2.


<!-- Page 59 -->

59

NNEML code tracking loop timing jitter σth from thermal noise is modelled as

σth = ⌜ ⃓ ⃓ ⃓ ⃓ ⎷ Bn ∫︁ Bfe/2 −Bfe/2 S(f) sin(πfDTc)df (2π) 2C/N0 (︂∫︁ Bfe/2 −Bfe/2 fS(f) sin(πfDTc)df )︂2

× ⌜ ⃓ ⃓ ⃓ ⃓ ⎷ 1 + ∫︁ Bfe/2 −Bfe/2 S(f) cos(πfDTc)df T × C/N0 (︂∫︁ Bfe/2 −Bfe/2 S(f) cos(πfDTc)df )︂2 , (39)

where S(f) is power spectral density of the modulated signal normalized to unit area over infinite bandwidth, Tc is code chip period, D is early-late correlator spacing in chips, C/N0 is carrier-to-noise density ratio, Bn = 1 Hz is DLL loop filter bandwidth, Bfe is receiver front-end bandwidth, and T = 1 ms is coherent signal integration time used in signal tracking \[14, p. 194-195\].

### 5.4 CNAV-2 navigation message decoding

The signal tracking module of FGI-GSRx produces streams of prompt correlator results for both GPS L1C pilot and data channels IP and IP,data at 1 ms intervals. Since each GPS L1C overlay chip or CNAV-2 symbol spans a 10 ms in time, the results were averaged over 10 intervals to improved SNR. The L1C overlay codes and CNAV-2 messages are synchronized so message beginnings were searched for by correlating local replica overlay codes L1CO with the pilot channel correlator results. Tracked overlay code chips are obtained from a pilot channel prompt correlator IP using a decision rule

L1Cˆ︂O\[n\] = { 1 if ∑︁10n+9 k=10n IP \[k\] > 0

−1 if ∑︁10n+9 k=10n IP \[k\] < 0. (40)

The tracked overlay code is then cross-correlated with a local replica L1CO\[n\] and, if the result is above a user-defined threshold, the delay value n0 corresponding to the maximum correlation result is set as the beginning of a new overlay code and a new CNAV-2 navigation message. A threshold value of 1700 was used in the implementation with there being 1800 chips total in each code. As for the navigation message decoding, 18 seconds of data channel prompt correlation results are taken from the beginning of a new CNAV-2 message and summed over the 10 ms symbol duration

R\[n\] = 10( ∑︂n+1) k=10n+1 IP,data\[k\], (41)

where n = n0, ..., n0 + 1799 with n0 marking the beginning symbol of a new message. The results are modelled as normally distributed around two mean values correspond ing to the sent CNAV-2 symbols. Symbol variance is estimated from channel noise measurements N\[k\] defined in (34) as

σ 2 R\[n\] = 10( ∑︂n+1) k=10n+1 N\[k\]/2. (42)


<!-- Page 60 -->

60

5.4.1 Time-of-interval decoding

Time-of-interval decoding used for the GPS L1C receiver implementation follows a maximum likelihood approach suggested in IS-GPS-800 ICD \[11\]. In short, the receiver computes a log-likelihood for each of the possible 256 8-bit LSB sequences of BCH(51,8) encoded TOI words. A received 9-bit TOI word is then constructed by picking the 8-bits corresponding to the highest absolute log-likelihood as the word’s LSBs and setting the MSB of the word based on the sign of the log-likelihood. An AWGN channel model is used to model the uncertainty in each subframe 1 symbol. The implementation is described in algorithm 1.

Algorithm 1 Soft BCH decoder for CNAV-2 messages Input Soft-decision symbols R\[n\] and their variances σ 2 R\[n\], where n = 0, 1, ..., 51. Output Time-of-interval value TOI ∈ \[0, 399\]

for all n = 0, 1, ..., 51 do

zn ← log P(d\[n\] = 1 | R\[n\]) P(d\[n\] = −1 | R\[n\]) ≈ 2R\[n\] σ 2 R\[n\] for i = 0, 1, ..., 255 do Generate BCH(51,8) encoded word cj ∈ {0, 1}, where j = 0, 1..., 50 for candi date TOI word value i using generator polynomial 763 (octal).

for all k = 0, 1, ..., 51 do

Ci ← { z0 if k = 0 Ci + (1 − 2ck−1)zk if k = 1, ..., 51

ˆi ← arg max i |Ci |

TOI ← { ˆi if Cˆi > 0 ˆi + 256 if Cˆi < 0

5.4.2 Low-density parity check decoding

A typical method for decoding LDPC encoded messages is to use some variation of belief propagation (BP) \[79, ch. 8\]. A BP LDPC decoder works by computing marginal distributions for sent message symbols conditional on received symbols and a low-density parity check matrix. The effectiveness of a single parity check in correcting an erroneously received symbol is conditional on the probability with which the other symbols used in the check are correct. Therefore, the marginal distribution computation is iterated multiple times to improve the probability of correcting errors. The iterations are continued until either all parity checks defined in the LDPC matrix pass or a maximum number of iterations is reached.


<!-- Page 61 -->

61

The algorithm used for the receiver implementation is presented in detail in a book by Johannesson and Zigangirov \[79, ch. 8.5\]. The algorithm was chosen due to its intuitive yet powerful operation and fast implementation in MATLAB using sparse operations. The algorithm is a soft LDPC decoder that is applicable to different channel models. As with the TOI word decoding, additive Gaussian channel noise is used to model the a priori distributions of input symbols before belief propagation.

Algorithm 2 Soft LDPC decoder for deinterleaved CNAV-2 messages \[79, p. 535\] Parameters L-by-N LDPC matrix H; Number of iterations I Input Soft-decision symbols R\[n\] and their variances σ 2 R\[n\], where n = 0, ..., N −1. Output Decoded navigation message bits vˆn, where n = 0, 1, ..., N − 1

L(n) ← { l ∈ \[0, L − 1\] | Hln = 1 } N (l) ← { n ∈ \[0, N − 1\] | Hln = 1 }

for n = 0, 1, ..., N − 1 do

z (0) n ← log P(d\[n\] = 1 | R\[n\]) P(d\[n\] = −1 | R\[n\]) ≈ 2R\[n\] σ 2 R\[n\] for all l ∈ L(n) do

z (0) nl ← z (0) n

for i = 1, 2, ..., I − 1 do for all n ∈ N (l), where l = 0, 1, ..., L − 1 do

y (i) ln ← log 1 + ∏︁ n′∈N (l)\\{n} tanh (︂ z (i−1) z ′ l /2 )︂

1 − ∏︁ n′∈N (l)\\{n} tanh (︂ z (i−1) z ′ l /2 )︂

for all l ∈ L(n), where n = 0, 1, ..., N − 1 do

z (i) nl ← z (0) n + ∑︂ l ′∈L(n)\\{l} y (i) l ′n

for all n ∈ N (l), where l = 0, 1, ..., L − 1 do

y (I) ln ← log 1 + ∏︁ n′∈N (l)\\{n} tanh (︂ z (I−1) z ′ l /2 )︂

1 − ∏︁ n′∈N (l)\\{n} tanh (︂ z (I−1) z ′ l /2 )︂

for n = 0, 1, ..., N − 1 do

z (I) n ← z (0) n + ∑︂ l∈L(n) y (I) ln

vˆn ← { 0 if z (I) n > 0 1 if z (I) n < 0


<!-- Page 62 -->

62

5.5 Obtaining GPS L1C navigation solutions After broadcasted CNAV-2 navigation messages have been decoded for the tracked SVs, the GPS L1C receiver proceeds to a PVT module where receiver antenna position and GPS system time (GPST) are estimated. FGI-GSRx also estimates antenna velocity but this is not addressed in the thesis. Position and time solutions require signal sending times, arrival times, and satellite positions at the time of sending to be solved for at least four satellites. Times of sending according to SV atomic clocks are computed based on decoded CNAV-2 times-of-sending and tracked ranging codes. Signal’s sending time-of-week (TOW) counts the number of seconds since the beginning of the latest GPS week epoch and is calculated for a tracked GPS L1C signal as

t (p) s = 7000 s × ITOW + 18 × (TOI − 1) + 0.010 × (N (p) c + τ (p) /10230) \[s\],

where ITOW is interval-time-of-week of CNAV-2 subframe 2, TOI is time-of-interval of subframe 1, N(p) c is the number of ranging codes observed since the beginning of a decoded CNAV-2 message of a tracking channel p, and τ (p) is the measured code phase at the instant of the PVT solution. Code phases of signals at an arbitrary solution instant are linearly interpolated from their respective DLL code phase estimates. The times of sending measured in SV clock times are translated to GPST using broadcasted clock correction parameters and then used to compute satellite positions using SV ephemeris parameters. The clock corrections and SV orbital position computations were explained in section 3.5 of this thesis. The PVT module also requires an initial approximate receiver clock synchroniza tion to GPST time to initialize Gauss-Newton algorithm. FGI-GSRx obtains the synchronization by assuming that it takes around 80 ms for a GPS signal to reach the receiver from a satellite on a MEO orbit. Signal time-of-arrival (TOA) is therefore approximated by simply adding 80 ms to the TOS of one of the tracked signals

t (1) r = t (1) s + 0.080 s. The Gauss-Newton algorithm used in FGI-GSRx to compute receiver antenna position and time bias between the initial rough estimate GPST time and actual GPST time at the time of the measurement has been explained briefly in section 3.5.4 of this thesis.


<!-- Page 63 -->

63

### 6 Experimental Setup

The L1C receiver implemented in the thesis was tested using both live and simulated I/Q signal data for a stationary GNSS reference antenna. The physical antenna is located at FGI’s Otaniemi premises and its reference ITRF2014 coordinates have been determined on 27-7-2022 using AUSPOS 2.4 Online GPS Processing Service and transformed into GRS 80 longitude, latitude, and ellipsoidal height. There exists a sub-millimetre difference between the semi-minor axes of the reference ellipsoids of GRS 80 and WGS 84 used by GPS but this difference is insignificant in case of the implemented receiver’s code-based positioning approach. The known location of the antenna was used to determine any bias present in navigation solutions. However, live GPS L1C broadcasts were missing their CNAV-2 messages at the time of receiver testing, so a GNSS simulator was used to generate signals corresponding to the exact reference antenna location.

6.1 Signal capture with Ettus USRP X310 A general purpose Ettus USRP X310 SDR was used for capturing GPS L1C signals for receiver testing. The USRP was fitted with SBX-120 transceiver daughterboard which can capture signals between 400 MHz and 4.4 GHz with an instantaneous bandwidth of 120 MHz \[80\]. With the daughterboard, GPS L1C signals could be recorded in raw I/Q format with a desired sampling rate, bandwidth, and sample size listed in table 10. The SBX-120 was operated in direct RF-to-baseband mode and a 10Gb Ethernet link was used to transfer the sample data to a computer which saved the data to a file. The reference antenna used for capturing GNSS signals was Septentrio PolaNt Choke Ring B3/E6 which is a high-precision multi-frequency GNSS antenna. Reference coordinates for the antenna and time of recording are listed in table 11. Sky plot in figure 23(a) shows the observed GPS Block III satellites above Espoo at the start of recording.

6.2 Signal generation with Safran Skydel GNSS simulator As GPS L1C was not fully operational at the time of receiver testing, a GNSS simulator was used to further verify the operation of the receiver. The simulator was especially used for testing receiver positioning with GPS L1C signals due to missing broadcast CNAV-2 messages and the low number of GPS Block III satellites in orbit. The simulator used for the data generation was Safran Skydel GNSS simulation software which is a comprehensive tool for testing and developing various tools and applications of GNSS. The same reference location and time of recording listed in table 11 were used in the simulated scenario as with the live capture. Satellite ephemerides and clock information needed to define SV orbits and clock states within Skydel were obtained in RINEX 3.04 format from NASA’s Archive of Space Geodesy Data. Sky plot in figure 23(b) shows the simulated satellites above Otaniemi at the start of simulation. The raw GNSS signal output files generated by Skydel were in the same I/Q format as the captured signal as listed in table 10. To


<!-- Page 64 -->

64

make the results more meaningful and easier to validate, most common uncertainties related to GNSS pseudorange estimates were turned off in the simulator. Omitted errors included SV ephemeris and clock state errors, ionospheric and tropospheric biases, and multipath. Receiver noise and interfering GPS L1 C/A, P-code, and Galileo E1 OS and BDS B1C signals were included in the simulated data.

Front-end Ettus USRP X310 front-end Safran Skydel GNSS simulator Center frequency \[GHz\] 1.57542 1.57542

Sampling frequency \[MHz\] 25.00 25.00

Filter bandwidth \[MHz\] 25.00 25.00

Complex samples True True Sample size I/Q \[bits\] 16/16 16/16

Table 10: Front-end parameters for recorded and simulated data. The flexibility of USRP X310 and Skydel allowed GNSS signals to be captured and simulated with the same parameters. The bandwidth is defined as double-sided.

Longitude Latitude Height Date Start time Duration 60.182 260◦ 24.828 537◦ 47.248 m 28-09-2023 23:20:00 UTC 900 s

Table 11: Reference location and time for live and simulated test scenarios. Antenna location is given in GRS80 longitude, latitude, and ellipsoidal height.

6.3 FGI-GSRx receiver setup FGI-GSRx is a post processing receiver in the sense that it cannot track satellites in real time. The receiver reads raw I/Q samples stored in a file as its input and executes different DSP modules in order: 1. acquisition, 2. tracking, 3. navigation message decoding, 4. navigation solution computation. The output navigation solution includes receiver antenna position, velocity, and GNSS time. The receiver can adapt to different sample rates and input data formats. FGI-GSRx allowed for the tuning of its modules using a configuration file. Used acquisition settings for GPS L1C are summarized in table 12, tracking loop filter parameters in table 13, and code tracking NNEML discriminator parameters for (38) in table 14.


<!-- Page 65 -->

65

34 9

Galileo 14 0°

60 19 N

W E

S GPS N

W E

S 28 31 26 4

11

20

5 12 25 8 7

18 22 38 44 12 8 13 10

5 25 11 43 23 37

BDS 25

24 11 12

10 33

29

18 28 11 4

2 60°30° 0° 60°30°

(a) (b)

Figure 23: Sky plots of GPS, Galileo, and BDS satellites above FGI Otaniemi premises on 28-09-2023 23:20:00 UTC in (a) a live and (b) a simulated test scenario. Figure (a) is generated according to Trimble GNSS Planning \[81\] and only shows live GPS Block III satellites transmitting GPS L1C signals.

Coherent integration time Number of non-coherent integrations Searched Doppler interval Doppler Frequency step Code delay step Acquisition threshold

10 ms 1 \[−6, 6\] kHz 50 Hz 1/FS 9

Table 12: Parameters used for GPS L1C signal acquisition. Fs is sampling frequency.

Loop PULL IN BW COARSE TRACKING BW FINE TRACKING BW Damping ratio Loop gain FLL 100 Hz 50 Hz 10 Hz 1.5 0.7 PLL 15 Hz 10 Hz 10 Hz 0.5 0.2 DLL 1 Hz 1 Hz 1 Hz 0.7 1

Table 13: Tracking loop bandwidths, damping ratios, and loop gains used for tracking L1 band GPS signals with the loop filter architecture described in \[78\].

Parameter GPS L1 C/A BPSK(1) GPS L1CP BOC(1,1) GPS L1CP TMBOC(6,1,4/33) Early-late spacing D = 2δ \[chips\] 1 1/3 1/12

Slope |k| \[1 per chip\] of correlation peak 1 3 179/33

Table 14: Used NNEML parameters for different GPS L1-band signals.


<!-- Page 66 -->

66

### 7 Results

The GPS L1C receiver implemented for FGI-GSRx as part of the thesis produces a large amount of data from its different signal processing modules. Including all of the data within the thesis would be impractical so the results chapter focuses on validating and assessing the overall operation of the implemented acquisition, signal tracking, data decoding, and PVT modules.

7.1 Acquiring live GPS L1C signals

Receiver acquisition results for live GPS L1C signals comprise obtained acquisition test statistics for pilot-only and semi-coherent combined channel methods described in section 5.2 with the parameters defined in table 12. Table 15 and figure 24 show the obtained statistics for all searched satellite signals indexed by their SV PRN numbers. The satellites that were known to be present in the live scenario include SV4, SV11, SV18, and SV28 while the rest of the SVs were missing. The statistics for the missing satellites, i.e., statistics from background noise and interference, have been averaged in the table as they are assumed to be nearly equally distributed. The semi-coherent acquisition produced a mean test statistic improvement of 21.5% over the four present SVs compared to the pilot only method. Meanwhile, only a slight increase of 2.9% was observed over the 28 absent SV PRN numbers. The main takeaway from the result was that the semi-coherent acquisition produced higher test statistics than the pilot-only method for the present satellites without majorly affecting statistics from background. Using the semi-coherent acquisition increased the apparent rate of detection for GPS L1C signals while having little to no impact on the rate of false alarms as a constant detection threshold was kept.

SV4 SV11 SV18 SV28 Mean over absent SVs L1C pilot-only (L1CP) 13.67 35.06 10.16 48.97 7.572 L1C semi-coherent (L1CP & L1CD) 16.41 41.39 13.39 56.90 7.781

Increase 20.0% 18.1% 31.8% 16.2% 2.9%

Table 15: Pilot-only and semi-coherent acquisition test statistics for live GPS signals.

7.2 Tracking live GPS L1C signals

Figure 25 shows carrier-to-noise-density ratio (C/N0) estimated using equation (35) for the four present GPS Block III satellites tracked with local replica GPS L1 C/A codes or L1CP pilot codes modulated with either BOC(1,1) or TMBOC(6,1,4/33). It was observed that the TMBOC modulated L1CP had the highest average C/N0 out of the three tested signals. Table 16 shows time averaged ratios of measured C/N0 for the C/A and the TMBOC modulated L1CP signals, and, the BOC modulated and the TMBOC modulated L1CP signals.


<!-- Page 67 -->

67

1 3 5 7 9 11 13 15 17 19 21 23 25 27 29 31 0 10 20 30 40 50 60

SV PRN number L1CP: True negative True positive L1CP & L1CD: True negative True positive

Figure 24: Acquisition test statistics for live GPS L1C signals for SVs 1–32. Red line indicates a threshold value used for signal detection.

0 100 200 300 400 500 600 700 800 900 34 36 38 40 42 44 46 48

Time \[s\]

GPS L1 C/A: SV4 SV11 SV18 SV28 GPS L1CP BOC(1,1): SV4 SV11 SV18 SV28 GPS L1CP TMBOC(6,1,4/33): SV4 SV11 SV18 SV28

Figure 25: C/N0 values for tracked live GPS SVs for different L1 band ranging codes and subcarrier modulation components.

An average ratio of 0.773 was observed between the measured C/N0s of the L1CP BOC and L1CP TMBOC signals over the 900 s tracking period. The ratio was noticed to be lower than a defined 29/33 ≈ 0.879 power ratio between the two modulation types of the GPS L1C signal. The observed C/N0 ratio and the power ratio were not expected to match exactly as the TMBOC modulation suppresses interference from


<!-- Page 68 -->

68

other L1-band signals more than pure BOC(1,1). Most interfering power on the L1 band is distributed close to the center frequency of 1575.42 MHz which the higher frequency BOC(6,1) component of GPS L1C TMBOC modulation helps to suppress. As for the L1 C/A, an average ratio of 0.871 was observed between its C/N0 and the C/N0 of TMBOC tracked L1CP over the 900 s tracking period. A ratio between the minimum received terrestrial powers of the signals is −0.25 dB ≈ 0.944. The observed ratio was again lower than the signal power ratio and the effect was contributed to the better interference suppression provided by TMBOC modulation as compared to standard BPSK utilized by L1 C/A. However, there is significant variation between individual satellites with SV11 even having an observed C/N0 ratio close to one. Any singular obvious reason for the variability between SVs could not be identified and the ratios may be impacted by, e.g., randomness of the C/N0 estimates, varying background interference, and the still developing status of L1C signal broadcasts.

Signal SV4 SV11 SV18 SV28 All SVs L1 C/A 0.791 0.984 0.850 0.858 0.871 L1CP BOC(1,1) 0.769 0.783 0.760 0.781 0.773

Table 16: Time averaged observed C/N0 ratio between L1 C/A or L1CP BOC(1,1) and L1CP TMBOC(6,1,4/33) for tracked live satellites.

The main take-away form the observed C/N0s is that GPS L1C tracking with a local pilot code replica modulated using TMBOC(6,1,4/33) resulted in increased C/N0 over the L1 C/A and BOC(1,1) tracked L1C not only due to a higher carrier power but also due to better in-band interference suppression. An increased C/N0 impacts both the code timing precision and the robustness of GNSS signal tracking loops, ultimately resulting in higher accuracy in positioning and timing, and more reliable service in environments with limited signal coverage. The results also demonstrated that the receiver implementation could track live GPS satellites using local L1C pilot channel codes modulated by either BOC(1,1) or TMBOC(6,1,4/33), which allows flexibility in receiver design. Figure 26 shows obtained normalized GPS L1C pilot and data channel prompt correlator results for the tracked GPS SV18. The correlators in (a) and (b) show oscillating behaviour that is indicative of varying signal power. One possible ex planation for the oscillations was surface multipath fading caused by the SV’s low elevation angle of around 10◦ . The same behaviour was observed when tracking L1 C/A signal broadcasted from the same SV18 but not with the other low elevation GPS SV4 located at a different azimuth angle. The figure 26(b) shows the GPS L1C data channel correlator output R\[n\] summed over a 10 ms symbol period as defined in equation (41). The correlator output was noticed to lack all phase modulation as CNAV-2 messages are missing from L1C broadcasts. This meant that broadcast satellite clock and ephemeris information could not be accessed from live GPS L1C signals. The lack of messages was not entirely surprising as the new signal has not yet been declared operational. The same


<!-- Page 69 -->

69

results could be observed for all of the four tracked GPS Block III SVs. Due to the missing clock and ephemeris data, PVT solutions based on live GPS L1C signals only could not be achieved at the time of writing this thesis.

(a)

0 100 200 300 400 500 600 700 800 900 −2 −1 0 1 2

Time \[s\] IP QP

(b)

0 100 200 300 400 500 600 700 800 900 −2 −1 0 1 2

Time \[s\] Normalized R\[n\]

Figure 26: GPS L1CP TMBOC(6,1,4/33) normalized pilot in (a) and 10 ms averaged data channel in (b) in-phase prompt correlator results for GPS SV18.

7.3 CNAV-2 decoding with implemented receiver

Receiver CNAV-2 navigation message decoding was tested using Monte Carlo simula tion where messages were first generated with added channel noise and then decoded. Decoding outcomes were classified into either successes or failures based on whether the original message information was retrieved. The outcomes were assumed to be Bernoulli distributed with a decoding rate of success parameter dependent on the message subframe type and energy per symbol to noise density ratio (Es/N0). Es/N0 may be translated into GPS L1C data channel C/N0 using equation

Es/N0 = C/N0 × Ts, (43)

where Ts = 10 ms is one CNAV-2 symbol period. CNAV-2 subframe 1 decoding was tested by drawing N = 5000 9-bit TOI words randomly and encoding each word into their respective 52-symbol subframes. AWGN matching a desired Es/N0 was added to simulate the effects of a communication channel. BCH decoding algorithm described in 1 was then applied to each word with the simulation AWGN variance supplied to the algorithm as an estimate for the input soft-decision symbol variance. A decoding was deemed successful if the original randomly drawn 9-bit TOI word was retrieved. Decoding rate of success was estimated by dividing the number of successful decodings by the total number

<!-- Image omitted -->

<!-- Image omitted -->


<!-- Page 70 -->

70

generated words as

pˆ = ∑︁N j=1 Aj N , (44)

where Aj = 1 if the jth generated TOI-word was successfully decoded and Aj = 0 otherwise. Wilson score interval was used to model the uncertainty of the Monte Carlo parameter estimation due to a limited sample size. A 99% Wilson confidence interval for the rate of success p was calculated as

p ≈ 2Npˆ + z 2 ± z √︂ z 2 + 4Npˆ(1 − pˆ) 2(N + z 2 ) , (45)

where z = 2.5758 for 99% confidence bounds. Figure 27 shows the Monte Carlo estimated subframe 1 decoding rate of success alongside 99% Wilson score intervals as a function of energy per symbol to noise density ratios Es/N0.

−25 −20 −15 −10 −5 0 5 0 0.2 0.4 0.6 0.8 1

Energy per symbol to noise power density Es/N0 \[dB\]

Figure 27: Estimated CNAV-2 Subframe 1 decoding rate of success pˆ as a function of Es/N0 for an AWGN channel with 99% Wilson score confidence bounds.

CNAV-2 subframe 2 and 3 LDPC decoding rates of success were estimated in a similar manner to the subframe 1. Known correct encoded subframes 2 and 3 from Skydel simulator were interleaved and AWGN corresponding to a desired Es/N0 was added to simulate channel noise. A total of N = 1000 encoded messages were generated and then decoded using algorithm 2. Decoding rate of success p was estimated using equation (44) with successful decodings being defined as those where the original subframe symbols were retrieved. 99% percentile confidence bounds for pˆ were again estimated using equation (45). Figure 28 shows the obtained estimate p as a function of Es/N0 and maximum belief propagation iteration number I. Estimated decoding rates of success at different Es/N0 values were further used to estimate the minimum required signal C/N0 needed to utilize CNAV-2 navigation message data included in GPS L1C broadcasts. Table 17 shows the minimum estimated Es/N0, corresponding GPS L1C data channel C/N0 and total L1C C/N0 including the pilot channel needed to obtain a 50% decoding rate of success for CNAV-2 subframes. The main takeaway from the results was that the BCH encoded


<!-- Page 71 -->

71

−4 −3 −2 −1 0 1 2 3 4 5 6 7 8 9 10 11 0 0.2 0.4 0.6 0.8 1 (a)

Energy per symbol to noise power density Es/N0 \[dB\]

−4 −3 −2 −1 0 1 2 3 4 5 6 7 8 9 10 11 0 0.2 0.4 0.6 0.8 1 (b)

Energy per symbol to noise power density Es/N0 \[dB\] I = 0 I = 1 I = 2 I = 3 I = 5 I = 10 I = 30

Figure 28: Estimated CNAV-2 subframe 2 (a) and subframe 3 (b) decoding rate of success p with dashed line 99% Wilson score confidence bounds as a function of Es/N0 and maximum belief propagation iteration number I.

subframe 1 from a single CNAV-2 message can be decoded at a considerably lower carrier to noise density ratio than the LDPC encoded subframes 2 and 3 with less redundancy bits.

Subframe Es/N0 \[dB\] L1C data C/N0 \[dB-Hz\] L1C total C/N0 \[dB-Hz\] 1 -10.1 ± 0.4 9.9 ± 0.4 15.9 ± 0.4 2 -2.14 ± 0.03 17.86 ± 0.03 23.88 ± 0.03 3 -2.03 ± 0.06 17.97 ± 0.06 23.99 ± 0.06

Table 17: Minimum Es/N0 and C/N0 required to achieve at least 50% decoding rate of success for different CNAV-2 subframes.

The better FEC performance of CNAV-2 subframe 1 in comparison to CNAV-2 subframes 2 and 3 can be a desired property for many modern GNSS receivers that access the slowly varying subframes 2 and 3 data from external assisting sources like mobile networks. The TOI-data included in subframe 1 is needed more often than the other subframes for resolving message and signal time-of-sending modulo 18


<!-- Page 72 -->

72

seconds. Assisting data is not readily available in FGI-GSRx so the whole CNAV-2 decoding process needs to be considered when assessing the functionality of the implemented GPS L1C receiver. However, the tracking loop utilized in FGI-GSRx loses signal lock below 28 dB-Hz C/N0, which means that the receiver’s CNAV-2 decoding performance for AWGN-type channels is of little concern unless the tracking loop is first made to be more robust.

7.4 User positioning with simulated GPS L1C signals

Receiver positioning was tested by comparing receiver positioning error to theoretically estimated values within the GPS L1C signal simulation setup described in chapter 6.2. Position solutions were computed from pseudorange measurements for 12 GPS satellites tracked using GPS L1CP codes with local replicas modulated using either BOC(1,1) or TMBOC(6,1,4/33). Positioning solutions were also obtained for GPS L1 C/A signals to verify that the receiver works in expected manner with the legacy signal. Table 18 includes a summary of the simulated positioning scenario including mean dilution of precision (DOP) values over the simulation period. DOP measures the impact of GPS constellation geometry on the accuracy of position or timing solutions. The values can be used to roughly predict positioning deviation from a true location for a receiver. Typically, DOP values below two are considered as indicative of excellent geometry. Within the thesis, the receiver positioning results were compared to more precisely modelled theoretical positioning solutions as described in the later section 7.4.2 so the DOP values were not considered further when assessing the receiver’s operation. Since the L1 C/A and L1C are transmitted from the same GPS satellites, the impact of constellation geometry on positioning is common for all of the tested signals.

Nr. sol. Nr. SV Mean C/N0 L1 C/A Mean C/N0 L1C BOC Mean C/N0 L1C TMBOC Mean HDOP Mean VDOP Mean PDOP 892 12 44.85 45.61 46.73 0.83 1.18 1.45

Table 18: Summary of simulated scenario’s signal C/NO and horizontal (HDOP), vertical (VDOP), and 3D-position (PDOP) dilution-of-precision values. Appendix 31 shows the individual C/N0 values for each of the tracked SVs and signals over the simulation period.

The table 18 also lists receiver estimated C/N0 values for the tracked signals averaged over the simulation period and all 12 tracking channels. It was noticed that the ratio between the L1 C/A and the L1C did not match the value observed with the live signals discussed in section 7.2. This was identified to be caused by an incorrect division of carrier power between L1C pilot and data channels in the Skydel GNSS simulator. The simulator appears to follow a 1:9 data-pilot power ratio rather than the 1:3 given for the L1C signal in the IS-GPS-800 interface control document \[11\]. The effects of varying C/N0 have been considered when evaluating the receiver’s positioning precision from a theoretical perspective.


<!-- Page 73 -->

73

7.4.1 Receiver positioning results

Figure 29 shows receiver estimated position solutions in relation to the receiver’s known true location in local ENU tangent plane coordinates. A position’s east (E), north (N), and up (U) coordinates correspond to position offsets from the true location to the stated directions with negative values indicating offset to the opposite, i.e., west, south, or down directions. The plots also show fitted 95% confidence ellipses and intervals for the position solutions assuming a Gaussian error distribution. Coordinate means, standard deviations, and RMS errors from the reference location are shown in table 19. The RMS error is provided for horizontal and vertical components separately as, due to constellation geometry, vertical positioning error tends to be much higher than horizontal error.

(a)

−3 −2 −1 0 1 2 3 −3 −2 −1 0 1 2 3

East deviation \[m\] 0 200 400 600 800 −6 −4 −2 0 2 4 6 (b)

Time \[s\]

L1 C/A L1CP BOC(1,1) L1CP TMBOC(6,1,4/33)

Figure 29: Receiver horizontal (a) and vertical (b) position deviation from the reference location for GPS L1 C/A, L1CP BOC(1,1), or L1CP TMBOC(6,1,4/33). Solid lines mark the 95 percentile confidence ellipses in (a) and intervals in (b).


<!-- Page 74 -->

74

GPS code RMS error \[m\] & modulation Mean \[m\] E/N/U STD \[m\] E/N/U Horizontal Vertical 3D

L1 C/A BPSK(1) -0.2550/ -0.0770/ -0.6359 0.6933/ 1.0083/ 1.9839 1.2517 2.0823 2.4295

L1C BOC(1,1) 0.0212/ -0.0464/ 0.0310 0.3038/ 0.4090/ 0.8063 0.5118 0.8064 0.9551

L1C TMBOC (6,1,4/33) -0.0013/ -0.0010/ -0.0029 0.0817/ 0.1239/ 0.2313 0.1483 0.2312 0.2747

Table 19: Observed means and standard deviations (STD) for solved east (E), north (N), and up (U) coordinates from reference as well as the horizontal, vertical, and 3D root-mean-squared errors (RMSE) from the reference location.

7.4.2 Theoretical position RMS deviation

The simulated testing scenario used for testing positioning with the implemented receiver discarded many common GNSS pseudorange measurement errors present in live signals such as atmospheric delay, satellite ephemerides and clock errors, and multipath. The remaining error was assumed to consist of code timing jitter caused by noise and tracking error due to high order satellite and user dynamics. FGI-GSRx uses a carrier aided code tracking loop where carrier frequency is used to estimate ranging code dynamics. This effectively eliminates timing jitter due to dynamics in code-based positioning \[14, p. 196\] leaving thermal noise as the sole dominant source of error for pseudorange measurements. Code tracking jitter due to thermal noise and interference was estimated theo retically using equation (39). Three variables in the equation were varied between the three tested signals: normalized PSD, correlator spacing D, and carrier-to-noise density ratio C/N0. Modelled tracking jitter as a function of C/N0 for the signals is shown in figure 30. The three curves in the figure that do not correspond to the tested receiver configurations indicate modelled DLL tracking jitter if BPSK(1) or BOC(1,1) modulated signals were tracked using narrower early-minus late spacings at the same 25 MHz front-end bandwidth. These curves are shown to demonstrate that the choice of early-late spacing has significant impact on ranging precision and that subcarrier modulation and carrier-to-noise ratio do not alone explain the observed positioning error variations between tested signals discussed in section 7.4.1. The least-squares positioning solution of equation (21) used for GPS positioning allowed positioning error in each dimension to be theoretically modelled as the geometry matrix A was known for the simulated constellation and ranging errors for different satellites could be modelled using (39). The pseudorange error vector ∆ρ of the equation was assumed to follow a multivariate normal distribution with zero mean and a diagonal covariance matrix Σρ with elements obtained by numerically evaluating (39). By the properties of linear maps, receiver positioning deviation from


<!-- Page 75 -->

75

25 30 35 40 45 50 0 0.5 1 1.5 2 2.5 3

Carrier to noise density ratio C/N0 \[dB-Hz\] BPSK(1), D = 1 BPSK(1), D = 1/3 BPSK(1), D = 1/12 BOC(1,1), D = 1/3 BOC(1,1), D = 1/12 TMBOC(6,1,4/33), D = 1/12

Figure 30: Theoretical tracking DLL tracking jitter \[m\] for different modulation types, early-late spacing values D, and carrier-to-noise density ratios C/N0 at 1 coherent integration time and 25 MHz front-end bandwidth.

a true position ∆x is zero mean multivariate normal distributed with covariance matrix Σx = (ATA)−1A TΣρA(ATA)−1 . (46) The theoretically obtained covariance matrix was averaged over the 900s simulation period since GPS satellite positions and signal C/N0 change slightly during the time. The carrier-to-noise density ratios used to estimate DLL tracking jitter were obtained for each satellite from the receiver estimated C/N0 shown in appendix 31. The values had estimation error, but it was assumed that the error was small enough such that its effects on positioning could be considered small. Table 20 lists positioning RMS errors in the simulated testing scenario observed for the receiver and the corresponding theoretical values estimated by drawing 100 million samples from the modelled multivariate error distributions.

GPS code & modulation Horizontal RMSE \[m\] Receiver / Theory Vertical RMSE \[m\] Receiver / Theory 3D-RMSE \[m\] Receiver / Theory L1 C/A BPSK(1) 1.252 / 1.314 2.082 / 2.098 2.430 / 2.476

L1CP BOC(1,1) 0.512 / 0.398 0.806 / 0.637 0.955 / 0.751

L1CP TMBOC (6,1,4/33) 0.148 / 0.091 0.231 / 0.145 0.275 / 0.171

Table 20: Receiver obtained and theoretically modelled positioning RMS errors in the simulated receiver testing scenario.


<!-- Page 76 -->

76

7.4.3 Comparing receiver positioning to theory

The RMS error values in table 20 indicate an expected and overall good level of performance for the implemented GPS L1C receiver although the observed values for the implementation were somewhat higher than the theoretical estimates. There are a few possible explanations for the discrepancy such as sampling error due to the limited number of 892 receiver position solutions and uncertainties related to DLL timing jitter modelling such as loop filter design that was not explored in detail during the thesis, and an assumption made that a simple C/N0 value can model the effects of both thermal noise and interference accurately. Receiver and theoretical position RMS errors obtained with the GPS L1 C/A were observed to be both larger and relatively closer to each other than with the GPS L1C. On a practical level, the decimetre level precision displayed by the implemented FGI-GSRx GPS L1C receiver is more than sufficient for most research uses. Quite often, GNSS positioning error is dominated by meter level ranging biases that were neglected in the simulation, such as atmospheric delay and multipath. The shown receiver positioning results are considered to validate the receiver’s tracking and PVT modules for use with good quality signals as the results demonstrated that the receiver could produce precise position estimates generally in-line with theory from simulated GNSS I/Q data.


<!-- Page 77 -->

77

### 8 Discussion

The goal of thesis was to develop a functioning GPS L1C software receiver that could be used to conduct research on satellite navigation in the future. The results described in the previous chapter showcased the outcomes from the tests conducted on the four main signal processing modules of the implemented L1C receiver using both real and simulated GNSS signal data. This discussion chapter goes over implications of the results, limitations of the research and the receiver design, and suggests some paths to develop the FGI-GSRx GPS L1C receiver further in the future.

8.1 Implications of GPS L1C signal for future GPS position ing

The proposed receiver implemented for FGI-GSRx was able to acquire and track GPS L1C signals broadcasted from live GPS Block III satellites. It was observed that the received carrier-to-noise density ratio was higher for the GPS L1C signals than the legacy L1 C/A which was contributed to the signal’s higher carrier power and reduction of in-band interference. The higher available C/N0 helps receivers to maintain tracking in environments with heavy attenuation and interference. To benefit from the increased C/N0, GPS L1C receivers have to utilize the whole TMBOC modulation of the L1C pilot channel, which necessitates the use of wide front-end bandwidths that include the BOC(6,1) modulated components of the signal. Capturing both sidebands of the BOC(6,1) modulation requires the use of at least around 15 MHz bandwidth as indicated in the figure 5. The GPS L1C can also be acquired and tracked at a lower front-end bandwidth in which case only the BOC(1,1) modulated part of the signal is be received. This was demonstrated in the thesis by tracking the L1C signal with a local replica modulated using only the BOC(1,1) component of TMBOC. The lack of BOC(6,1) limited the available carrier power and maximum code timing precision but would have also allowed for lowered front-end bandwidth and sampling rate. Lower sampling rates allow receivers to operate with better efficiency which can be especially helpful during signal acquisition when timing precision is not prioritized. Commercial GNSS receivers with relaxed requirements for accuracy can opt to only use the BOC(1,1) component of the L1C signal and still benefit from the signal’s various new features and improved precision compared to the legacy L1 C/A. However, the L1C is not expected to completely replace the capabilities of the L1 C/A as the BPSK modulated signal still allows for even lower minimum front-end bandwidths to be used in low-precision and low-power applications. The C/A code can also be acquired with less power due to the shorter ranging code period which may be useful for receivers that do not continuously track signals and only produce PVT solutions when needed by acquiring the signal again every time. In general, GPS L1C signal will provide higher accuracy compared to the L1 C/A at the same front-end bandwidth. How impactful the improvement is, depends on the application, receiver design, and available methods for compensating other GNSS errors. As an example, it was noticed from figure 30 that BPSK(1), BOC(1,1),


<!-- Page 78 -->

78

and TMBOC(6,1,4/33) modulated signals are all capable of offering below half a meter ranging precision at a nominal C/N0 above 40 dB-Hz and a high front-end bandwidth of 25 MHz. Such precision is more than sufficient for common GNSS users as the accuracy is anyways limited by atmospheric biases and satellite orbit and clock errors. According to the figure, timing jitter of a BOC signal increases slower with decreasing C/N0 than of a BPSK signal, which suggests that the extra precision offered by GPS L1C may become more and more impactful as signal conditions worsen. All in all, the thesis results showed that the new GPS L1C signal will offer more options for receiver designers to achieve desired precision and power usage constraints set for L1-band GPS receivers by adjusting front-end bandwidth, sampling rate, and local replica modulation.

8.2 Impact and limits of the thesis’s results The GPS L1C receiver implemented in the thesis was successful in acquiring and tracking live GPS Block III satellites using GPS L1C signals. The receiver was able to decode CNAV-2 messages and estimate valid position solutions from simulated I/Q-data. The results of the thesis demonstrated that each of the main modules of the FGI-GSRx receiver adapted for GPS L1C use worked in an expected manner and that the receiver can be utilized in future research projects. Adopting the L1C receiver for research use is straightforward as it is implemented as part of the FGI-GSRx receiver used widely at the Finnish Geospatial Research institute. Topics for future research could include how to best utilize the signal structures of GPS L1C, e.g., how to optimally utilize L1C overlay codes for fast receiver time synchronization, or how to combine properties of GPS L1C and L1 C/A signals to best benefit from the two signals in different applications and environments. Both the real and simulated I/Q data used for receiver testing in the thesis represented ideal signal conditions where an antenna had an excellent visibility to the sky. The testing procedure did not address the receiver’s operation in all the widely varying environments that a GNSS user may find themselves in. While it was verified that the receiver can track signals and produce navigation solutions, tracking and positioning performance may be heavily impacted by channel effects such as multipath and atmospheric disturbances. It is therefore of interest to continue to test the receiver using live L1C I/Q data captured at different environments and with preferably moving users. Recording live GPS L1C signals at different times of day and over long duration of time will become more feasible in the future as more GPS Block III satellites are launched during the current decade. The simulation-based analysis on implemented CNAV-2 decoding algorithms presented in section 7.3 could be helpful in designing receivers for very weak GPS L1C signals. Weak signal acquisition and tracking is relevant for, e.g., receivers operating under interference, at extreme north and south latitudes, and for orbit determination of satellites located at the fringes of GPS SV antenna gain patterns. The presented relationships between signal SNR and CNAV-2 decoding rate of success can help to predict when available ES/N0 becomes a limiting factor for utilizing the


<!-- Page 79 -->

79

L1C signal. How well the analysis conducted using an AWGN model generalizes to varying real-life channel conditions was however left unexplored. The analysis also assumed that signal C/N0 stays constant over a message period and that there are no interruptions in signal tracking. Further research would be needed to better account for the limitations in channel modelling and symbol erasures caused by, e.g., periodic loss of signal lock. The comparison of the receiver positioning RMS error to theory was used to validate the operation of the GPS L1C receiver tracking and PVT modules. RMS errors for L1 C/A signal were also obtained to verify whether an existing signal implementation in FGI-GSRx matched theoretical expectations and as a point of comparison for the GPS L1C. However, since a different DLL early-minus late spacings were used for the C/A, BOC-modulated L1C, and TMBOC-modulated L1C signals, the observed positioning RMS values were not easily comparable. Instead, the comparison between the signals was approached from a theoretical viewpoint. Testing the receiver using common correlator spacing values for the different codes at varying front-end bandwidths could have provided data for a more comprehensive analysis on the performance of the implementation. This would have provided insight into how to tune the receiver for different front-ends and operational requirements.

8.3 Considering the future development of the GPS L1C receiver The GPS L1C receiver implementation of the thesis can be viewed as a baseline solution needed to utilize the new signal and there remains room for future improve ments. Some possibly impactful features of the L1C, e.g., overlay code and data channel tracking, were not considered in the thesis at all. Exploring and utilizing these features of the signal requires further development of the receiver. First, the thesis’s receiver implementation did not fully utilize the L1C overlay codes. The codes are not required just for synchronizing CNAV-2 messages but can also be used for predicting and removing the remaining secondary code phase modulation present on the L1C pilot channel. A pilot channel lacking any phase modulation allows a receiver to utilize four-quadrant inverse tangent (atan 2) FLL and PLL discriminators instead of the two-quadrant ones defined in equations (36) and (??). The four-quadrant discriminators are less prone to carrier cycle slips \[14, p. 184–191\], which makes a receiver less likely to lose signal lock at low C/N0 values. Similarly, the utilized NNEML DLL discriminator of equation (38) could be replaced by a coherent equivalent which would not necessitate the squaring of correlator outputs. This would reduce code tracking noise and improve both stability and timing precision of the delay-locked loop. Another tracking module change that could be introduced to the receiver is to use both the pilot and data channels of the L1C signal to estimate carrier and code states. Dual channel tracking could be implemented using, e.g., semi-coherent method as was done within the implemented signal acquisition module. The added carrier power from the data channel would result at best in around 1.25 dB-Hz increase to available C/N0 which would however be reduced by the growing rate


<!-- Page 80 -->

80

of data channel phase estimation errors as C/N0 decreases. It is possible that a semi-coherent combined channel L1C tracking method could prove to be of little benefit as only small improvements towards maintaining signal lock at low C/N0 can be achieved while the computational load of tracking is also increased. For further reference, general combined pilot and data channel tracking has been explored in \[82\] and more specifically for L1-band GPS signals in \[83\]. A major limiting factor of the FGI-GSRx GPS L1C receiver observed during the thesis was exceedingly long processing times. Even with a high-end computer, acquisition of 32 GPS satellites with the 10230 chip long L1C codes took up to multiple minutes and signal tracking over a 15 minute period took up to a few days. While this does not prevent the receiver’s usage in research, it can heavily slow down development and research projects where long I/Q files have to be processed. The slow operation can be contributed in part to the core receiver architecture, but also to a lack of code optimization techniques favored for MATLAB such as a focus on matrix operations rather than loops. Finding faster signal processing algorithms, eliminating redundant math operations, and optimizing data structures should improve the receiver performance considerably. Better processing efficiency would not only help with the new GPS L1C implementation but also with all the existing signal implementations of the FGI-GSRx receiver.


<!-- Page 81 -->

81

### 9 Conclusion

The thesis aimed to address a need for new receiver tools that can utilize the new GPS L1C signal coming online during the current decade. As part of the thesis, a GPS L1C implementation was developed for FGI-GSRx software receiver. Tests run on the receiver with live and simulated GNSS I/Q data shown in chapter 7 demonstrated that the receiver can acquire and track GPS L1C signals as well as decode CNAV-2 navigation messages to produce usable PVT solutions. The results validated the implemented receiver modules, gave insight into the performance of the BCH and LDPC decoding methods adopted for CNAV-2, and compared the receiver’s positioning precision to theoretical predictions. All in all, the work conducted in the thesis produced a functioning GPS L1C receiver that can be used in future research projects conducted at the Finnish Geospatial Research Institute and hopefully elsewhere as well. The thesis included a wide look into GNSS technologies in chapters 2–4 which offer a great starting point for anybody interested in GNSS technology and especially the new GPS L1C signal. The approach towards developing the L1C receiver followed quite closely the examples set by other signal implementations of FGI-GSRx receiver and GNSS Software Receivers book \[8\]. Anybody familiar with the FGI-GSRx receiver should be able to easily start utilizing the L1C receiver as well. There exists a goal to integrate the L1C signal processing modules into an open-source version of FGI-GSRx with a complementary paper planned for the ION GNSS+ 2024 conference in September. The open-source version will offer the wider GNSS research community the tools to acquire, track, and utilize the new GPS L1C signal for any research purpose where real time processing is not a requirement. Section 8.1 of the thesis discussed the implications of the new L1C signal on future GPS L1-band service from a mostly theoretically perspective. The discussion relied on modelled impacts of constellation geometry and code timing jitter from limited carrier power, noise, modulation type, and code tracking parameters described in the section 7.4.2. The main conclusion from the results was that the new GPS L1C signal will supplement the existing L1 C/A by providing more precise and robust signal tracking with its TMBOC modulation and higher carrier power. Utilizing the improved tracking properties of the L1C will require a wider front-end bandwidth than the L1 C/A leading to higher computational burden and more susceptibility to certain types of interference. It was identified that, by offering different capabilities to the L1 C/A, the new L1C signal can introduce more flexibility to receiver designs and allows GPS receivers to be better optimized for different applications by balancing precision, receiver complexity, and power usage. Section 8.2 and 8.3 discussed the limits of the thesis research and paths to further improve the implemented GPS L1C receiver. The main take-away from the chapters was that there remains room to better characterize and optimize the implemented receiver by running tests using different configurations in varying channel conditions, and by implementing improved L1C signal tracking where the overlay codes of the signal are synchronized during tracking time to enable the use of coherent discriminators. Further testing and receiver improvements could be used to gain


<!-- Page 82 -->

82

insight into the operation of GPS L1C receivers in less ideal signal conditions than were tested during the thesis. Continuing research into robust positioning was considered as the logical next step for both improving the implemented receiver and gaining an even better understanding of the real impacts the new GPS L1C signal can have on the future GPS L1-band service.


<!-- Page 83 -->

83

## References

\[1\] D. Gebre-Egziabher and S. Gleason, GNSS applications and methods. Boston, MA, USA: Artech House, 2009.

\[2\] M. Tran, “Other Global Navigation Satellite Systems (GNSS),” gps.gov, Oct. 2021. \[Online\]. Available: https://www.gps.gov/systems/gnss/

\[3\] B. Hofmann-Wellenhof, H. Lichtenegger, and E. Wasle, GNSS - Global Navigation Satellite Systems : GPS, GLONASS, Galileo, and more. Wien, Austria: Springer, 2008.

\[4\] “GPS Standard Positioning Service Performance Standard,” U.S. Office of the Department of Defense, Washington, DC, USA, 5th ed., 2020.

\[5\] “GLONASS Open Service Performance Standard,” Information and Analysis Center for Positioning, Navigation and Timing, Korolev, Russia, ed. 2.2, 2020. \[Online\]. Available: https://glonass-iac.ru/upload/docs/stehos/stehos\_en.pdf

\[6\] “Galileo-Open Service-Service Definition Document,” European GNSS Agency, Prague, Czech Republic, issue 1.2, 2021. \[Online\]. Available: https://www. gsc-europa.eu/sites/default/files/sites/all/files/Galileo-OS-SDD\_v1.2.pdf

\[7\] “BeiDou Navigation Satellite System Open Service Parformance Standard,” China Satellite Navigation Office, Beijing, China, ver. 3.0, 2021. \[Online\]. Available: http://en.beidou.gov.cn/SYSTEMS/Officialdocument/ 202110/P020211014595952404052.pdf

\[8\] K. Borre, I. Fernández-Hernández, J. A. López-Salcedo, and M. Z. H. Bhuiyan, GNSS Software Receivers. Cambridge, UK: Cambridge University Press, 2022.

\[9\] L. Jacobson, GNSS markets and applications, 3rd ed., ser. GNSS technology and applications. Norwood, MA, USA: Artech House, 2007, ch. 2.5.

\[10\] “Galileo Open Service - Signal-in-Space Interface Control Document,” European GNSS Agency, Prague, Czech Republic, issue 2.0, 2021. \[Online\]. Available: https://www.gsc-europa.eu/sites/default/files/sites/all/files/Galileo\_ OS\_SIS\_ICD\_v2.0.pdf

\[11\] “NAVSTAR GPS Space Segment/User Segment L1C Interfaces,” Science Applications International Corporation (SAIC), El Segundo, CA, USA, IS-GPS-800J, 2022. \[Online\]. Available: https://www.gps.gov/technical/icwg/

\[12\] “GLONASS ICD: Code Division Multiple Access Open Service Navigation Signal in L1 frequency band,” Russian Space Systems, JSC, Moscov, Russia, ed. 1.0, 2016.

\[13\] C. J. Hegarty, “GNSS signals—An overview,” in 2012 IEEE International Frequency Control Symposium Proceedings, Baltimore, MD, USA, May 2012, pp. 1–7. \[Online\]. Available: https://doi.org/10.1109/FCS.2012.6243707


<!-- Page 84 -->

84

\[14\] E. Kaplan and C. Hegarty, Understanding GPS/GNSS : principles and applica tions, 2nd ed. Norwood, MA, USA: Artech House, 2006.

\[15\] S. Shanmugam, C. Mongredien, J. Nielsen, and G. Lachapelle, “Design of short synchronization codes for use in future GNSS system,” International Journal of navigation and Observation, vol. 2008, Art. no. 246703. \[Online\]. Available: https://doi.org/10.1155/2008/246703

\[16\] J. J. Rushanan, “The spreading and overlay codes for the L1C signal,” Navigation, vol. 54, pp. 43–51, 2007. \[Online\]. Available: https://doi.org/10.1002/j.2161-4296.2007.tb00394.x

\[17\] N. C. Shivaramaiah, A. G. Dempster, and C. Rizos, “Exploiting the secondary codes to improve signal acquisition performance in Galileo receivers,” in Proceedings of the 21st International Technical Meeting of the Satellite Division of The Institute of Navigation (ION GNSS 2008), Savannah, GA, USA, Sept. 2008, pp. 1497–1506. \[Online\]. Available: https://doi.org/10.26190/unsworks/725

\[18\] O. Richard, “Old, but Still Useful: The Manchester Code,” digikey.com, Apr. 2022. \[Online\]. Available: https://www.digikey.com/en/blog/ old-but-still-useful-the-manchester-code

\[19\] E. S. Lohan, A. Lakhzouri, and M. Renfors, “Binary-offset-carrier modulation techniques with applications in satellite navigation systems,” Wireless Communications and Mobile Computing, vol. 7, no. 6, pp. 767–779, 2007. \[Online\]. Available: https://doi.org/10.1002/wcm.407

\[20\] J. W. Betz, “Binary Offset Carrier Modulations for Radionavigation,” Navigation, vol. 48, no. 4, pp. 227–246, 2001. \[Online\]. Available: https://doi.org/10.1002/j.2161-4296.2001.tb00247.x

\[21\] R. Swider, D. Dickshinski, R. Robb, and J. Martel, “GPS selective availability: A retrospective,” in Proceedings of the IAIN World Congress and the 56th Annual Meeting of The Institute of Navigation (2000), San Diego, CA, USA, June 2000, pp. 319–324.

\[22\] European GNSS Agency, “GNSS User Technology Report,” issue 3, 2020. \[Online\]. Available: https://op.europa.eu/en/publication-detail/-/publication/ 73477ef0-3516-11eb-b27b-01aa75ed71a1/language-en

\[23\] W. Emmer and E. Watts, “Atomic frequency standards for the GPS IIF satellites,” in Proceedings of the 29th Annual Precise Time and Time Interval Systems and Applications Meeting, Long Beach, CA, USA, Dec. 1997, pp. 201–212.

\[24\] G. X. Gao, S. Datta-Barua, T. Walter, and P. Enge, “Ionosphere effects for wideband GNSS signals,” in Proceedings of the 63rd Annual Meeting of The Institute of Navigation (2007), Cambridge, MA, USA, Apr. 2007, pp. 147–155.


<!-- Page 85 -->

85

\[25\] C. Dunn, D. Jefferson, S. Lichten, J. Thomas, Y. Vigue, and L. Young, “Time and position accuracy using codeless GPS,” in Proceedings of the 25th Annual Precise Time and Time Interval Systems and Applications Meeting, Pasadena, CA, USA, Dec. 1993, pp. 169–182.

\[26\] B. C. Barker, J. W. Betz, J. E. Clark, J. T. Correia, J. T. Gillis, S. Lazar, K. A. Rehborn, and J. R. Straton, “Overview of the GPS M code signal,” in Proceedings of the 2000 National Technical Meeting of the Institute of Navigation, Anaheim, CA, USA, Jan. 2000, pp. 542–549.

\[27\] “New Civil Signals,” gps.gov, Aug. 2020. \[Online\]. Available: https: //www.gps.gov/systems/gps/modernization/civilsignals/

\[28\] “NAVSTAR GPS Space Segment/Navigation User Segment Interfaces,” Science Applications International Corporation (SAIC), El Segundo, CA, USA, IS-GPS-200N, 2022. \[Online\]. Available: https://www.gps.gov/technical/icwg/

\[29\] “NAVSTAR GPS Space Segment/User Segment L5 Interfaces,” Science Applications International Corporation (SAIC), El Segundo, CA, USA, IS-GPS-705J, 2022. \[Online\]. Available: https://www.gps.gov/technical/icwg/

\[30\] S. Thoelert, S. P., O. Montenbruck, and M. Meurer, “GPS III Arrived – An Initial Analysis of Signal Payload and Achieved User Performance,” in Proceedings of the 32nd International Technical Meeting of the Satellite Division of The Institute of Navigation (ION GNSS+ 2019), Miami, FL, USA, Sept. 2019, pp. 1059–1075.

\[31\] M. Stewart, “GPS III: Building on 200 years of On-Orbit PNT Excellence,” 2014. \[Online\]. Available: https://web.stanford.edu/group/scpnt/pnt/PNT14/ 2014\_Presentation\_Files/19.GPSIII-PNT%20Excellence-Stanford.pdf

\[32\] G. D. Krebs, “Spacecraft: Navigation - USA,” space.skyrocket.de. \[Online\]. Available: https://space.skyrocket.de/directories/sat\_nav\_usa.htm

\[33\] “50 SW completes GPS constellation expansion,” June 2011. \[On line\]. Available: https://www.af.mil/News/Article-Display/Article/113065/ 50th-space-wing-completes-gps-constellation-expansion/

\[34\] C. Rizos, M. Higgins, and G. Johnston, “Impact of Next Generation GNSS on Australasian Geodetic Infrastructure,” in FIG Congress 2010: Facing the Challenges–Building the Capacity, Sydney, Australia, Apr. 2010.

\[35\] V. Kazantsev, “The GLONASS and GLONASS-M Programs,” in Proceedings of the 8th International Technical Meeting of the Satellite Division of The Institute of Navigation (ION GPS 1995), Palm Springs, CA, USA, Sept. 1995, pp. 985–990.


<!-- Page 86 -->

86

\[36\] General Radio Frequency Center, “June 2, 2004 Resolution 609 (WRC-03) Consultation Meeting: Commitment of the GLONASS system regarding the compliance with the Resolution 609 criteria.” Dec. 2003. \[Online\]. Available: https://web.archive.org/web/20150226060247/http://groups.itu.int/ Portals/19/activeforums\_Attach/GLONASS%20Commitment%20Ltr.pdf

\[37\] B. Eissfeller, G. Ameres, V. Kropp, and D. Sanroma, “Performance of GPS, GLONASS and Galileo,” in 51st Photogrammetric Week, vol. 7, Heidelberg, Germany, Jan. 2007, pp. 185–199.

\[38\] R. B. Langley, “Innovation: GLONASS — past, present and future,” GPS World, vol. 28, no. 11, pp. 44–49, 2017. \[Online\]. Available: https://www.gpsworld.com/innovation-glonass-past-present-and-future/

\[39\] “GLONASS ICD: Navigational radiosignal in bands L1, L2,” Russian Institute of Space Device Engineering, Moscov, Russia, ed. 5.1, 2008.

\[40\] “GLONASS ICD: Code Division Multiple Access Open Service Navigation Signal in L2 frequency band,” Russian Space Systems, JSC, Moscov, Russia, ed. 1.0, 2016.

\[41\] “GLONASS ICD: Code Division Multiple Access Open Service Navigation Signal in L3 frequency band,” Russian Space Systems, JSC, Moscov, Russia, ed. 1.0, 2016.

\[42\] G. D. Krebs, “Spacecraft: Navigation - USSR / Russia,” space.skyrocket.de. \[Online\]. Available: https://space.skyrocket.de/directories/sat\_nav\_usa.htm

\[43\] “About GLONASS,” glonass-iac.ru. \[Online\]. Available: https://glonass-iac.ru/ en/about\_glonass/

\[44\] “Development of the BeiDou Navigation Satellite System,” China Satellite Navigation Office, Beijing, China, ver. 4.0, 2019. \[On line\]. Available: http://en.beidou.gov.cn/SYSTEMS/Officialdocument/202001/ P020200116329195978690.pdf

\[45\] “CNSS (Compass/BeiDou Navigation Satellite System),” eoportal.org. \[Online\]. Available: https://www.eoportal.org/satellite-missions/cnss

\[46\] “BeiDou Navigation Satellite System SIS ICD - Open Service Signal B1C,” China Satellite Navigation Office, Beijing, China, ver. 1.0, 2018. \[Online\]. Available: http://en.beidou.gov.cn/SYSTEMS/ICD/201806/ P020180608519640359959.pdf

\[47\] “BeiDou Navigation Satellite System SIS ICD - Open Service Signal B2a,” China Satellite Navigation Office, Beijing, China, ver. 1.0, 2017. \[Online\]. Available: http://en.beidou.gov.cn/SYSTEMS/ICD/201806/ P020180608518432765621.pdf


<!-- Page 87 -->

87

\[48\] “BeiDou Navigation Satellite System SIS ICD - Open Service Signal B2b,” China Satellite Navigation Office, Beijing, China, ver. 1.0, 2020. \[Online\]. Available: http://en.beidou.gov.cn/SYSTEMS/ICD/202008/ P020200803539206360377.pdf

\[49\] “BeiDou Navigation Satellite System SIS ICD - Open Service Signal B1I,” China Satellite Navigation Office, Beijing, China, ver. 3.0, 2019. \[Online\]. Available: http://en.beidou.gov.cn/SYSTEMS/ICD/201902/ P020190227702348791891.pdf

\[50\] “BeiDou Navigation Satellite System SIS ICD - Open Service Signal B3I,” China Satellite Navigation Office, Beijing, China, ver. 1.0, 2018. \[Online\]. Available: http://en.beidou.gov.cn/SYSTEMS/ICD/201806/ P020180608516798097666.pdf

\[51\] “BDS System Status - Constellation Status,” csno-tarc.cn. \[Online\]. Available: http://www.csno-tarc.cn/en/system/constellation

\[52\] G. D. Krebs, “Spacecraft: Navigation - China,” space.skyrocket.de. \[Online\]. Available: https://space.skyrocket.de/directories/sat\_nav\_china.htm

\[53\] “European GNSS Service Centre - Galileo - Services,” gsc-europa.eu. \[Online\]. Available: https://www.gsc-europa.eu/galileo/services

\[54\] “COSPAS-SARSAT - Transition to MEOSAR,” Montreal, Canada, 2014. \[On line\]. Available: https://cospas-sarsat.int/images/content/articles/Transition\_ to\_MEOSAR\_Updated\_2023-01-24.pdf

\[55\] J. Ángel Ávila Rodríguez, “On Generalized Signal Waveforms for Satellite Navigation,” Ph.D. dissertation, University FAF Munich, Munich, Germany, 2008.

\[56\] G. Hein, “GNSS Interoperability: Achieving a Global System of Systems or "Does Everything Have to Be the Same?",” Inside GNSS, vol. 1, no. 1, pp. 57–60, 2006. \[Online\]. Available: https://www.insidegnss.com/auto/0106\_ Working\_Papers\_IGM.pdf

\[57\] “European GNSS Service Centre - Galileo - Orbital and Technical Parameters,” gsc-europa.eu. \[Online\]. Available: https://www.gsc-europa.eu/ system-service-status/orbital-and-technical-parameters

\[58\] “European GNSS Service Centre - Galileo - Constellation Informa tion,” gsc-europa.eu. \[Online\]. Available: https://www.gsc-europa.eu/ system-service-status/constellation-information

\[59\] “The EU Space Programme - Galileo - Programme,” euspa.europa.eu, Oct. 2022. \[Online\]. Available: https://www.euspa.europa.eu/european-space/ galileo/programme


<!-- Page 88 -->

88

\[60\] C. Rizos, “Multi-constellation GNSS/RNSS from the perspective of high accuracy users in Australia,” Journal of spatial science, vol. 53, no. 2, pp. 29–63, 2008. \[Online\]. Available: https://doi.org/10.1080/14498596.2008.9635149

\[61\] L. Wang, P. D. Groves, and M. K. Ziebart, “Multi-constellation GNSS performance evaluation for urban canyons using large virtual reality city models,” The Journal of Navigation, vol. 65, no. 3, pp. 459–476, 2012. \[Online\]. Available: https://doi.org/10.1017/S0373463312000082

\[62\] G. Hein, T. Pany, S. Wallner, and J.-H. Won, “Platforms for a future GNSS receiver,” Inside GNSS, vol. 1, no. 2, pp. 56–62, 2006. \[Online\]. Available: https://www.insidegnss.com/auto/0306\_Working\_Papers\_IGM.pdf

\[63\] K. Yegin, “Antennas and Front-End in GNSS,” in Multifunctional Operation and Application of GPS, R. B. Rustamov and A. M. Hashimov, Eds. Rijeka, Croatia: IntechOpen, 2018. \[Online\]. Available: http://doi.org/10.5772/intechopen.71221

\[64\] F. Bastide, D. Akos, C. Macabiau, and B. Roturier, “Automatic gain control (AGC) as an interference assessment tool,” in Proceedings of the 16th Interna tional Technical Meeting of the Satellite Division of The Institute of Navigation (ION GPS/GNSS 2003), Portland, OR, USA, Sept. 2003, pp. 2042–2053.

\[65\] D. Borio, “A statistical theory for GNSS signal acquisition,” Ph.D. dissertation, Polytecnico di Torino, Turin, Italy, 2008.

\[66\] A. E. Süzer and H. Oktal, “A comparison analysis on forward error correction technology: a future perspective for GNSS,” Aircraft Engineering and Aerospace Technology, vol. 95, no. 8, pp. 1311–1320, 2023. \[Online\]. Available: https://doi.org/10.1108/AEAT-10-2021-0319

\[67\] “Galileo Open Service - Ionospheric Correction - Algorithm for Galileo Single Frequency Users,” European GNSS Agency, Prague, Czech Republic, issue 1.2, 2016. \[Online\]. Available: https://www.gsc-europa.eu/sites/default/files/sites/ all/files/Galileo\_Ionospheric\_Model.pdf

\[68\] J. A. Klobuchar, “Ionospheric time-delay algorithm for single-frequency GPS users,” IEEE Transactions on aerospace and electronic systems, vol. AES-23, no. 3, pp. 325–331, 1987. \[Online\]. Available: https: //doi.org/10.1109/TAES.1987.310829

\[69\] H. S. Hopfield, “Two-quartic tropospheric refractivity profile for correcting satellite data,” Journal of Geophysical Research (1896-1977), vol. 74, no. 18, pp. 4487–4499, 1969. \[Online\]. Available: https://doi.org/10.1029/JC074i018p04487

\[70\] J. Saastamoinen, “Atmospheric Correction for the Troposphere and Stratosphere in Radio Ranging Satellites,” in The Use of Artificial Satellites for Geodesy, S. W. Henriksen, A. Mancini, and C. B. H., Eds. American Geophysical Union (AGU), 1972, pp. 247–251. \[Online\]. Available: https://doi.org/10.1029/GM015p0247


<!-- Page 89 -->

89

\[71\] V. B. Mendes and R. B. Langley, “Tropospheric Zenith Delay Prediction Accuracy for High-Precision GPS Positioning and Navigation,” NAVIGATION, vol. 46, no. 1, pp. 25–34, 1999. \[Online\]. Available: https://doi.org/10.1002/j.2161-4296.1999.tb02393.x

\[72\] H. D. Black and A. Eisner, “Correcting satellite Doppler data for tropospheric effects,” Journal of Geophysical Research: Atmospheres, vol. 89, no. D2, pp. 2616– 2626, 1984. \[Online\]. Available: https://doi.org/10.1029/JD089iD02p02616

\[73\] A. E. Niell, “Global mapping functions for the atmosphere delay at radio wavelengths,” Journal of geophysical research: solid earth, vol. 101, no. B2, pp. 3227–3246, 1996. \[Online\]. Available: https://doi.org/10.1029/95JB03048

\[74\] J. Boehm and H. Schuh, “Vienna mapping functions in VLBI analyses,” Geophysical Research Letters, vol. 31, no. 1. \[Online\]. Available: https: //doi.org/10.1029/2003GL018984

\[75\] S. Bancroft, “An algebraic solution of the GPS equations,” IEEE transactions on Aerospace and Electronic Systems, vol. AES-21, no. 1, pp. 56–59, 1985. \[Online\]. Available: https://doi.org/10.1109/TAES.1985.310538

\[76\] M. Z. H. Bhuiyan, S. Söderholm, S. Thombre, L. Ruotsalainen, M. Kirkko Jaakkola, and H. Kuusniemi, “Performance evaluation of carrier-to-noise density ratio estimation techniques for BeiDou Bl signal,” in 2014 Ubiquitous Positioning Indoor Navigation and Location Based Service (UPINLBS), Corpus Christi, TX, USA, Feb. 2014, pp. 19–25. \[Online\]. Available: https://doi.org/10.1109/UPINLBS.2014.7033706

\[77\] M. Z. H. Bhuiyan and E. S. Lohan, “Multipath mitigation techniques for satellite-based positioning applications,” in Global Navigation Satellite Systems, S. Jin, Ed. Rijeka: IntechOpen, 2012, ch. 17. \[Online\]. Available: https://doi.org/10.5772/29137

\[78\] S. Thombre, M. Z. H. Bhuiyan, S. Söderholm, M. Kirkko-Jaakkola, L. Ruot salainen, and H. Kuusniemi, “A software multi-gnss receiver implementation for the indian regional navigation satellite system,” IETE Journal of Research, vol. 62, no. 2, pp. 246–256, 2016.

\[79\] R. Johannesson and K. S. Zigangirov, Fundamentals of convolutional coding, 2nd ed. Cambridge, MA, USA: John Wiley & Sons, 2015.

\[80\] “X300/X310,” kb.ettus.com, Oct. 2023. \[Online\]. Available: https: //kb.ettus.com/X300/X310

\[81\] “Trimble GNSS Planning Online 1.6.1.0,” 2017–2018. \[Online\]. Available: https://www.gnssplanning.com/


<!-- Page 90 -->

90

\[82\] D. Borio, “GNSS Data/Pilot Combining with Extended Integrations for Carrier Tracking,” Sensors, vol. 23, no. 8, 2023, Art. no. 3932. \[Online\]. Available: https://doi.org/10.3390/s23083932

\[83\] Macchi-Gernot, Florence and Petovello, Mark G and Lachapelle, Gérard and others, “Combined acquisition and tracking methods for GPS L1 C/A and L1C signals,” International Journal of Navigation and Observation, vol. 2010, Art. no. 190465. \[Online\]. Available: https://doi.org/10.1155/2010/190465


<!-- Page 91 -->

91

100 200 300 400 500 600 700 800 900 38 40 42 44 46 48 50 52

Time \[s\]

100 200 300 400 500 600 700 800 900 38 40 42 44 46 48 50 52

Time \[s\]

100 200 300 400 500 600 700 800 900 38 40 42 44 46 48 50 52

Time \[s\]

SV9 SV18 SV4 SV5 SV12 SV26 SV20 SV11 SV31 SV28 SV25 SV29

Figure 31: C/N0 values for all tracked GPS L1 C/A (top), L1CP BOC(1,1) (middle), and L1CP TMBOC(6,1,4/33) (bottom) signals in the simulated testing scenario described in chapter 6.2.

