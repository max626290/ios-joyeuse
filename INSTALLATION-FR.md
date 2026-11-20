# Essai iOS 16.7.16 sur Redmi Note 9 Pro joyeuse

Ce paquet expérimental vise uniquement **joyeuse**, avec écran tactile Novatek
NT36675 Tianma. Le noyau avec le pilote a compilé. Le démarrage complet et le
tactile n'ont pas encore été validés sur ce téléphone. Le premier essai peut
nécessiter des corrections, notamment du brochage SPI.

## État des fichiers

La préparation produit dans `out/package/` :

- `shim-boot.img` : démarrage temporaire, noyau et configuration Novatek ;
- `ios16-root.simg` : système iOS 16.7.16, build 20H392, pour userdata ;
- `manifest.json` et `root-expanded.json` : tailles et empreintes de contrôle.

La présence de ces quatre fichiers et la réussite de `finish-package.py` sont
requises. Une compilation du noyau seule ne constitue pas un paquet installable.
Les radios utilisent des identifiants locaux synthétiques ; leur fonctionnement
n'est pas validé. Ce système ne convient pas à des données personnelles.

## Prérequis sur le téléphone

Le dernier contrôle montrait un bootloader verrouillé. Il doit être déverrouillé
par la procédure officielle Xiaomi avant tout démarrage d'image personnalisée.
L'outil officiel peut imposer une attente liée au compte Xiaomi ; les scripts
ne contournent pas cette attente. Le déverrouillage efface les données.

L'outil officiel téléchargé sur ce PC est `../tools/mi-unlock/miflash_unlock.exe`.
Dans MIUI, utiliser le même compte Xiaomi dans le téléphone et dans cet outil.
L'association se fait dans Paramètres > Paramètres supplémentaires > Options
pour les développeurs > Statut de déverrouillage Mi > Ajouter un compte et un
appareil. Si les options développeur sont masquées, toucher plusieurs fois la
version MIUI dans À propos du téléphone. Suivre ensuite l'outil officiel :
téléphone éteint, maintenir Volume bas + Power pour fastboot, brancher l'USB et
lancer Unlock. Si un délai est affiché, le respecter et conserver le même compte.
La connexion au compte et les éventuelles validations doivent être faites par
le propriétaire ; ne pas communiquer le mot de passe dans le chat.

Sources officielles : [téléchargement Xiaomi](https://en.miui.com/unlock/download_en.html)
et [FAQ du déverrouillage](https://www.mi.com/global/support/faq/details/KA-07238/).

Pour sauvegarder les partitions, démarrer temporairement un recovery compatible
avec **joyeuse** et disposant d'ADB root. Aucune image de recovery n'est incluse
ni prétendue validée ici. Ne pas choisir une image pour sweet ou topaz.

## Commandes Windows

Ouvrir PowerShell dans le dossier `ios-joyeuse`. Python et les outils Android
du dossier voisin `tools/platform-tools` doivent être présents.

1. Contrôler la connexion USB :

   ```powershell
   .\Telephone.ps1 status
   ```

2. Depuis le recovery compatible, sauvegarder les partitions du téléphone :

   ```powershell
   .\Telephone.ps1 backup
   ```

   Les sauvegardes et leurs empreintes sont dans `backups/first`. Le script
   exige cette sauvegarde pour écrire le système. Ne pas la supprimer.

3. Revenir en fastboot (Power + Volume bas), puis écrire le système.
   **Cette commande efface le contenu Android de userdata.**

   ```powershell
   .\Telephone.ps1 flash-root -Experimental -EraseData
   ```

4. Démarrer temporairement iOS :

   ```powershell
   .\Telephone.ps1 boot -Experimental
   ```

Ces scripts vérifient le modèle, le déverrouillage et les empreintes. Ils
n'écrivent pas boot, recovery, modem ou les calibrations. Le démarrage utilise
`fastboot boot`, pas `fastboot flash boot`. Un arrêt du pilote sur un identifiant
de puce inconnu est volontaire : ne pas supprimer ce contrôle pour forcer l'essai.

## Retour à Android

Revenir en fastboot avec Power + Volume bas. Pour reformater les données :

```powershell
.\Telephone.ps1 restore-android-data -EraseData
```

Puis redémarrer le téléphone. Android retrouvera ses partitions système
préservées, avec des données effacées. Si le formatage fastboot ne suffit pas,
utiliser le formatage des données du recovery adapté. Ne pas reverrouiller le
bootloader tant que le système officiel n'est pas entièrement restauré.

## Réception du paquet préparé sur le serveur

Le transfert se fait en morceaux chiffrés, supprimés du serveur après réception,
afin de limiter le stockage des artefacts. La clé reste dans `fw/transfer.key`.
Après réception complète, exécuter en remplaçant RUN_ID par le numéro réel :

```powershell
python tools/finish-package.py out/transfer-RUN_ID
```

Ce contrôle vérifie les empreintes des fichiers et celle de l'image reconstituée.
Il ne valide pas le fonctionnement matériel du téléphone.
