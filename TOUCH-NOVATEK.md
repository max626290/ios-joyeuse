# Diagnostic tactile joyeuse — 12 novembre 2026

## Extraction officielle terminée — 13 novembre 2026

Archive Fastboot EEA V14.0.5.0.SJZEUXM récupérée depuis cdnorg.d.miui.com,
4 852 634 070 octets. MD5 conforme à l'index :
`a94f3350b525f506323c69ab56336e74`. Archive et images conservées localement.
Les métadonnées LP de super.img ont aussi passé les contrôles SHA-256.

Extrait de vendor : `fw/novatek_ts_tianma_fw.bin`, 139264 octets,
SHA-256 `1a27ab58c49dbe3b7cfd1864711512a414ba3a1ee767b4b7831f1e8b7538bedd`.
Le fichier `_mp.bin` est distinct (tests de fabrication), ne pas le sélectionner
comme firmware normal. Le firmware FocalTech est également présent : le paquet
contient plusieurs variantes, et sa présence ne prouve pas le matériel monté.

DTBO officiel décodé : reset Novatek GPIO 8, interruption GPIO 9, SPI maximum
8 MHz, reset logiciel 0x3f0fe et fast-read 0x3f310, identiques à la référence
Android examinée. L'overlay annonce à la fois FocalTech et Novatek. Les réglages
de dalle incluent NT36675 Tianma ; confirmation du chip ID physique encore requise.
Les DTS et l'inventaire sont dans `fw/stock/`. Aucun flash effectué.

## Pilote compilé — 13 novembre 2026

Le patch 0119 ajoute `sweet_novatek.h` : décodage transactionnel de dix
contacts, détection des paquets de récupération, rejet des doublons et des
coordonnées hors écran, et émission de relâchements.

`mkadt.py --touch-controller novatek` sélectionne maintenant explicitement
la famille. Le patch 0120 raccorde ce décodage au transport SPI et au service
HID. Il vérifie l'identifiant NT36675, transfère le firmware officiel et relit
les blocs écrits avant de démarrer la lecture des contacts. Les broches choisies
explicitement sont CLK 55, MOSI 53, MISO 54, CS 56 ; cet ordre reste à confirmer
sur le téléphone. Il n'y a pas de recherche automatique de brochage.
Les ADT historiques et la sélection ft8756 conservent le fonctionnement ancien.

Le noyau incluant ces deux patches a compilé dans l'exécution GitHub
43405019892, source 211c917. Les tests locaux du décodeur et du transport simulé
ont réussi. Cela ne prouve ni le démarrage d'iOS ni le fonctionnement matériel
du tactile : aucun essai iOS sur le téléphone n'a encore été effectué.

Le téléphone est un appareil de test : son propriétaire autorise les
effacements de userdata nécessaires aux essais. Cette autorisation ne couvre
pas la suppression des calibrations ou des autres partitions protégées.
Le bootloader reste verrouillé au dernier contrôle ; aucun flash effectué.

## Résultat observé sur le téléphone

ADB autorisé, Android fonctionnel, bootloader verrouillé. `getevent -lp` identifie
`NVTCapacitiveTouchScreen`, dix emplacements multitouch, coordonnées X 0–1079
et Y 0–2399. `/proc` expose `NVTSPI` et les entrées `nvt_*`. Cela établit la
famille Novatek et indique son interface SPI, mais pas le numéro de puce.

La lecture de `/proc/tp_info`, `/proc/tp_lockdown_info`, `/proc/nvt_fw_version`,
des modalias SPI et des firmwares est refusée à l'utilisateur ADB actuel.
Ce refus ne signifie pas que les fichiers ou le matériel sont absents.

Reproduction depuis la racine du dépôt sous Windows :

```powershell
python tools/touch-audit.py --adb ../tools/platform-tools/adb.exe --output logs/touch-audit-2026-11-12.json
python -B -m unittest discover -s tests -p test_touch_audit.py
```

Les preuves locales restent dans `logs/`, exclu de Git. Aucun redémarrage,
déverrouillage, accès brut au SPI ou écriture sur le téléphone n'a été effectué.

## Incompatibilité dans le portage actuel

Base examinée : `3743f7db05a04f50214bf4969a80885eebb32a23`.
`0098-sweet-ft8756-spi.patch` met en œuvre FocalTech FT8756, et `tools/mkadt.py`
injecte un firmware sous `/chosen/focaltech-firmware` pour joyeuse.
Ce n'est pas le protocole du contrôleur Novatek détecté. Renommer un fichier
firmware ou remplacer une chaîne de modèle ne résoudrait pas cette différence.
Nous n'avons pas démarré iOS : il s'agit d'une incompatibilité identifiée en
préparation, pas de la cause démontrée d'un échec iOS observé sur cet appareil.

## Référence Android examinée

Source : https://github.com/LineageOS/android_kernel_xiaomi_sm6250
Branche lineage-21, commit `0c870bf38789d65e6153d4b11c0eb70783d1ad7c`.
Extraits locaux dans `research/novatek-reference/`, exclus de Git.
Ce noyau de référence n'est pas une extraction du noyau MIUI installé.

- `drivers/input/touchscreen/nt36xxx_spi/nt36xxx.c` : SPI mode 0, mots de
  8 bits, lecture avec un octet factice ; le premier octet utile est pris
  à `rbuf[2]`. Les masques lecture/écriture sont distincts de FocalTech.
- `nt36xxx.h` : firmware Tianma `novatek_ts_tianma_fw.bin`, avec un nom
  générique `novatek_ts_fw.bin` selon la configuration.
- `nt36xxx_mem_map.h` : plusieurs identités prises en charge. NT36675 est
  reconnu par les trois derniers octets `75 66 03`; ne pas choisir la carte
  mémoire sans vérifier l'identité matérielle.
- `nt36xxx_fw_update.c` : chargement du firmware, partitions, contrôles CRC
  et vérification de l'état de démarrage. Un firmware simplement présent
  dans l'ADT ne suffit pas : le pilote doit le transférer correctement.
- `arch/arm64/boot/dts/qcom/touchscreen.dtsi` : un même nœud annonce FocalTech
  et Novatek. Il référence QUP SE11, GPIO reset 8, IRQ 9, limite SPI 8 MHz,
  reset logiciel `0x03f0fe`, registre fast-read `0x03f310`.
  Le champ `interrupts` contient 13 tandis que la propriété Novatek indique 9 :
  à confronter au DTB réel et à l'utilisation des GPIO par le pilote.
  Ces valeurs sont des références, pas une mesure de notre appareil.
- La sélection Tianma et le texte NT36675 dans le pilote renforcent cette
  hypothèse, mais ne confirment ni le fabricant de dalle ni la puce de notre
  téléphone.

## Format des contacts et intégration envisagée

Le pilote lit 65 octets de données via un tampon logique de 66 octets avec
l'adresse en position 0. Dix enregistrements de six octets commencent à
`1 + 6*i`. L'identifiant est `b0 >> 3`; les états 1 et 2 sont actifs.
`x = (b1 << 4) | (b3 >> 4)` et `y = (b2 << 4) | (b3 & 15)`.
Les contacts absents du rapport doivent être relâchés. Les paquets de réveil,
de récupération du firmware et les erreurs SPI ne sont pas des contacts.

Une future implémentation doit distinguer sélection du contrôleur, transport
SPI, identification, chargement du firmware, validation des rapports et
transmission à `sweet_hid_touch`. Elle doit refuser une identité inconnue et
conserver le chemin FocalTech pour les appareils qui l'utilisent réellement.
Les coordonnées doivent suivre les mêmes conventions que le service HID,
sans appliquer deux fois la mise à l'échelle vers le canevas iPhone X.

## Conditions pour poursuivre les essais matériels

1. Obtenir l'identité du contrôleur, le firmware exact et le DTB du téléphone.
   L'accès ADB actuel ne le permet pas ; une image officielle correspondant
   à V14.0.5.0.SJZEUXM peut fournir des références sans effacer le téléphone,
   mais il faudra encore confirmer la variante montée.
2. Préparer un hôte macOS / GitHub Actions pour compiler XNU et une méthode
   de construction du système iOS. Aucun choix fourni par l'utilisateur à ce stade.
3. Sauvegarder les données avant un éventuel déverrouillage (qui les efface),
   puis sauvegarder les partitions de calibration via un accès adapté.
4. Valider d'abord identification et transport avec logs, puis firmware et
   contacts. Aucun pilote Novatek XNU opérationnel n'est livré à ce stade.

## Validation réalisée

Les deux tests `test_novatek.py` passent : sélection ADT, reconstruction de
sweet_touch.c et du header depuis la série de patches, puis compilation et
exécution du harnais C avec Zig 0.13.0 (cc, C11, Wall/Wextra/Werror).
Le harnais teste dix contacts, le dernier pixel, la pression, les relâchements,
les trames tronquées, les doublons et les marqueurs de récupération.
Ce sont des trames synthétiques, pas des captures SPI de notre téléphone.
Les tests d'images existants ne passent pas tous sous Windows (os.chown et
outils hôte absents) ; `mise run check` reste non exécuté car mise est absent.
La première compilation GitHub a échoué avant toute étape, faute de capacité
des runners macOS ; une relance gratuite a été demandée.

Le collecteur a été exécuté sur le téléphone. Ses deux tests passent, notamment
le refus d'inférer un FT8756 à partir d'informations absentes. Cela ne valide
ni un pilote XNU, ni une compilation du noyau, ni le fonctionnement sous iOS.
La suite complète du dépôt reste non validée sous Windows (voir PREPARATION-IOS.md
dans le dossier parent).
