# -*- coding: utf-8 -*-
import os, re

# Путь к книге (можно задать переменной окружения K2_PATH)
K2_PATH = os.getenv("K2_PATH", "KeytoFate_arbeiten.txt")

def _load_corpus() -> str:
    """Читает текст книги из K2_PATH или из /app/KeytoFate_arbeiten.txt (для Railway/Docker)."""
    try:
        if os.path.exists(K2_PATH):
            with open(K2_PATH, "r", encoding="utf-8") as f:
                return f.read()
        alt = "/app/KeytoFate_arbeiten.txt"
        if os.path.exists(alt):
            with open(alt, "r", encoding="utf-8") as f:
                return f.read()
    except Exception as e:
        print(f"[WARN] corpus load error: {e}")
    return ""

CORPUS_TEXT = _load_corpus()

def _extract_numbered_sections(corpus: str, heading_regex: str) -> dict[int, str]:
    """
    Вытягивает блоки по заголовкам вида:
      Geisteszahl 1
      Handlungszahl 8
      Verwirklichungszahl 3
      Ergebniszahl 7
      Gemeinsame Geisteszahl 4
    """
    out: dict[int, str] = {}
    if not corpus:
        return out

    pat = re.compile(heading_regex, re.I | re.M)
    matches = list(pat.finditer(corpus))
    if not matches:
        return out

    for i, m in enumerate(matches):
        try:
            n = int(m.group(1))
        except Exception:
            continue
        start = m.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(corpus)
        block = corpus[start:end].strip()
        # чистим лишние пустые строки и одиночные нумерации
        block = re.sub(r'\n{3,}', '\n\n', block)
        block = re.sub(r'\n\s*\d+\s*\n', '\n', block)
        out[n] = block
    return out

# Разделы из книги
GEISTES_FULL   = _extract_numbered_sections(CORPUS_TEXT, r'^\s*(?:##\s*)?Geisteszahl\s+([1-9])\s*$')
HANDLUNGS_FULL = _extract_numbered_sections(CORPUS_TEXT, r'^\s*(?:##\s*)?Handlungszahl\s+([1-9])\s*$')
VERWIRK_FULL   = _extract_numbered_sections(CORPUS_TEXT, r'^\s*(?:##\s*)?Verwirklichungszahl\s+([1-9])\s*$')
ERGEBNIS_FULL  = _extract_numbered_sections(CORPUS_TEXT, r'^\s*(?:##\s*)?Ergebniszahl\s+([1-9])\s*$')
PARTNER_FULL   = _extract_numbered_sections(CORPUS_TEXT, r'^\s*(?:##\s*)?Gemeinsame\s+Geisteszahl\s+([1-9])\s*$')

def get_geistes(n: int) -> str:   return (GEISTES_FULL.get(n) or "").strip()
def get_handlungs(n: int) -> str: return (HANDLUNGS_FULL.get(n) or "").strip()
def get_verwirk(n: int) -> str:   return (VERWIRK_FULL.get(n) or "").strip()
def get_ergebnis(n: int) -> str:  return (ERGEBNIS_FULL.get(n) or "").strip()
def get_partner(n: int) -> str:   return (PARTNER_FULL.get(n) or "").strip()

# -*- coding: utf-8 -*-
from typing import Dict

# Короткие аннотации по Geisteszahl (1–9)
GEISTES_TXT = {
    1: "(Menschen, geboren am 1., 10., 19., 28.) — Führung, starker Wille, Initiative.",
    2: "(2., 11., 20., 29.) — Harmonie, Diplomatie, empathisches Verstehen.",
    3: "(3., 12., 21., 30.) — Wissen, Ausdruck, Kreativität.",
    4: "(4., 13., 22., 31.) — Struktur, Ordnung, Ausdauer.",
    5: "(5., 14., 23.) — Bewegung, Kommunikation, Chancen.",
    6: "(6., 15., 24.) — Liebe, Fürsorge, Verantwortung.",
    7: "(7., 16., 25.) — Weisheit, Wahrheit, Disziplin.",
    8: "(8., 17., 26.) — Management, Erfolg, Gerechtigkeit.",
    9: "(9., 18., 27.) — Dienst, Mitgefühl, Vollendung.",
}

# Краткие подписи для Vollanalyse
HANDLUNG_SHORT = [
    'Direkt/Initiativ','Verbindend/Diplomatisch','Kommunikativ/Wissensorientiert',
    'Strukturiert/Verlässlich','Flexibel/Chancenorientiert','Fürsorglich/Verantwortungsvoll',
    'Transformativ/Diszipliniert','Zielorientiert/Belastbar','Dienend/Abschließend'
]
VERWIRK_SHORT = [
    'Führung & Strategie','Beziehungen & Partnerschaften','Wissen, Lehre & Ausdruck',
    'Strukturen & Systeme','Expansion & Kommunikation','Liebe & Weisheit',
    'Exzellenz & Bühne','Materieller Erfolg','Dienst & höchste Weisheit'
]
ERGEBNIS_SHORT = [
    'Reife Führung','Echte Kooperation','Ausdruck & Wissen','Struktur & Vollendung',
    'Freiheit in Bewusstheit','Liebe mit Weisheit','Transformation & Tiefe',
    'Gerechter Erfolg','Dienst & Großzügigkeit'
]

# Tagesenergie 1–9
TAG_TXT = {
    1: "Neuer Zyklus, klare Entscheidungen, erste Schritte.",
    2: "Dialog, Ausgleich, Partnerschaft, ehrliche Gespräche.",
    3: "Kommunikation, Lernen, Reisen, inspirierender Austausch.",
    4: "Struktur, Planung, praktische Arbeit, Ordnung schaffen.",
    5: "Chancen, Bewegung, Netzwerke, flexible Lösungen.",
    6: "Harmonie, Familie, Schönheit, reife Verantwortung.",
    7: "Analyse, Spiritualität, Hygiene des Geistes.",
    8: "Management, Finanzen, Ergebnisse, Leistung.",
    9: "Abschluss, Dienst, Großzügigkeit, Raum für Neues.",
}

# Краткие описания для Kollektivenergie (без Entwicklungspfad)
KOLLEKTIV_TXT = {
    1: "Initiativen, starke Persönlichkeiten, Führung. Vision bündeln, Rollen klären.",
    2: "Verbindend, ausgleichend, Wir-Gefühl. Verantwortung verankern, ehrlich sprechen.",
    3: "Austausch, Ideen, Lernen. Prioritäten & Prozesse halten Fokus.",
    4: "Strukturiert, ausdauernd, stabil. Innovation zulassen, nicht erstarren.",
    5: "Beweglich, chancenorientiert, Netzwerke. Innerer Kompass & Ziele.",
    6: "Sorgend, wertorientiert, ästhetisch. Faire Lasten, Balance Nähe/Freiheit.",
    7: "Forschend, diszipliniert, tief. Ergebnisse teilen, Wissen anwenden.",
    8: "Leistungsstark, zielorientiert, Management. Transparenz & Ethik.",
    9: "Sinnstiftend, humanitär, abschließend. Grenzen wahren, Erholung.",
}

# Полные тексты дней рождения 1–31 (твои длинные блоки)
DAY_BIRTH_TXT: Dict[int, str] = {
    1: """Bedeutung des Geburtstages 1 Sie besitzen ein absolut reines Bewusstsein, eine junge Seele. Sie haben wenige Zweifel, aber viel Entschlossenheit, zu handeln und voranzugehen. Nutzen Sie unbedingt Ihr Führungspotential!
Manchmal leiden Menschen, die am 1. Tag geboren sind, unter Pessimismus oder sie sind von anderen enttäuscht. Dies geschieht, weil nicht alle in ihrer Umgebung bereit sind, sich mit ihrer „führenden“ Meinung abzufinden.
Es wird empfohlen, sich mit Psychologie zu beschäftigen und die Energie des Verstehens anderer Menschen zu entwickeln – also stets nach gegenseitigem Verständnis zu streben. Außerdem wird allen Einsen empfohlen, die Energie des Gebens und der Barmherzigkeit zu kultivieren.""",

    2: """Bedeutung des Geburtstages 2 Sie sind der beste Ratgeber und Helfer in allen Angelegenheiten. Nehmen Sie aktiver an Führungsaufgaben teil, da nur Sie in der Lage sind, schwierige Situationen tief und detailliert zu durchdringen.
Ihr Bewusstsein ist auf die ständige Suche nach Kontakten und den Aufbau vertrauensvoller Beziehungen ausgerichtet. Doch gerade der Bereich der Beziehungen ist der Punkt, an dem eine ernsthafte innere Arbeit notwendig ist.
Im negativen Zustand können Sie unter Problemen in Beziehungen, Unentschlossenheit und ständigen Zweifeln leiden. Um Ihr Bewusstsein zu erweitern, sollten Sie mit neuen Menschen in Kontakt treten und Psychologie studieren, um die Struktur anderer Menschen richtig zu verstehen.""",

    3: """Bedeutung des Geburtstages 3 Ihnen steht die Energie des Wissens zur Seite, daher kann es so wirken, als ob Sie alles selbst wissen. Sie neigen dazu, nur Fachleuten auf ihrem Gebiet zu vertrauen und hören nicht auf andere Menschen, da Sie glauben, dass diese schlechter informiert sind als Sie.
Indem Sie sich durch die Weitergabe von Wissen verwirklichen, werden Sie noch klüger und erfolgreicher. Menschen, die an diesem Tag geboren sind, müssen ständig Neues lernen. Dazu eignen sich Kurse, Bücher, Schulen, Universitäten und andere Formen der Bildung.
Wenn Sie genügend Wissen angesammelt haben, können Sie der beste Lehrer in Ihrem Fachgebiet werden. Eine Ihrer Aufgaben besteht darin, ein Mentor für andere Menschen zu sein und Ihr Wissen weiterzugeben – genau das macht Sie zu einem erfolgreichen Menschen.
Darüber hinaus können Sie sich auch in Bereichen verwirklichen, die mit dem Umgang und der Verwaltung von Geldmitteln verbunden sind (Buchhalter, Analyst, Schatzmeister) sowie im Bereich des Reisens.""",

    4: """Bedeutung des Geburtstages 4 Ihre Energie besteht aus maximaler Kreativität und dem Streben nach Gerechtigkeit. Lernen Sie, sich zu erden, und treiben Sie unbedingt Sport, damit die Energie in Ihren Körper gelangt.
Ihr Bewusstsein schwebt oft in Träumen und Fantasien, und es muss wieder auf die Erde, in den Körper, zurückgeführt werden.
Oft leben Menschen, die an diesem Datum geboren sind, in einem Zustand eines „unausgeglichenen Mechanismus“ (wie auch andere „Vieren“). Aus diesem Zustand können Sie nur durch die Arbeit mit Ihrem Körper herauskommen.
Sie sollten Ihre Energie durch Sport oder Yoga steigern und Ihre gesamte Aufmerksamkeit auf Kreativität richten. Wenn Sie diese Empfehlungen befolgen, verbessern Sie schnell alle Lebensbereiche und erreichen jene Harmonie, nach der Ihr träumerischer Geist strebt.""",

    5: """Bedeutung des Geburtstages 5 Sie haben eine feine Wahrnehmung dieser Welt, was Sie angemessener handeln lässt als andere. Dies kann bei Ihnen zu zahlreichen Verletzungen und emotionaler Verspanntheit führen, was Ihren physischen Körper schädigen kann. Die Hauptaufgabe besteht darin, Verständnis zu entwickeln und die effektivste Kommunikation mit Ihren Partnern aufzubauen.
In einem positiven Geisteszustand erfüllen Sie eine wichtige Aufgabe: Sie sind das Bindeglied zwischen verschiedenen Menschen. Deshalb haben Sie große Erfolge im Business, Marketing und in allen anderen Bereichen, die mit Kommunikation und Expansion zu tun haben. Ihre Energie strebt danach, alles um Sie herum zu erweitern und zu verbreiten, manchmal führt dies jedoch zu negativen Konsequenzen. Diese können sich in der Veränderlichkeit und Leichtfertigkeit zeigen, zu der die Energie der Zahl 5 neigt. Es ist wichtig, zu lernen, Ihre Aufmerksamkeit über längere Zeit auf ein Projekt oder eine Person zu konzentrieren, bis Ihre Arbeit echte Früchte trägt.""",

    6: """Bedeutung des Geburtstages 6 Das Bewusstsein ist darauf ausgerichtet, maximalen Komfort zu erhalten und zu schaffen. Sie werden Glück haben, besonders wenn Sie innere Weisheit und Liebe zu den Menschen entwickeln. Sie haben eine entwickelte Verbindung zum Göttlichen, daher müssen Sie immer auf Ihr Herz hören.
Die Hauptaufgabe für Sie ist es, zu lernen, alle Ihre Angelegenheiten zu Ende zu bringen. Die Energie der Zahl 6 ist sehr weise, strebt aber gleichzeitig nach Genuss. Deshalb erreichen viele Projekte und Aufgaben die Phase des Abschlusses nicht. Sie müssen Ihre Disziplin und Willenskraft entwickeln, denn jedes abgeschlossene Projekt macht Sie stärker. In diesem Fall werden Sie immer von Glück und Erfolg begleitet.""",

    7: """Bedeutung des Geburtstages 7 Wahrscheinlich lieben Sie Sport seit Ihrer Kindheit und besitzen eine große Energie-Reserve. Es ist sehr wichtig für Sie, zu lernen, sich Ziele zu setzen, denn diese Energie sollte für deren Erreichung aufgewendet werden, nicht für die Schaffung von Chaos in Ihrem Leben.
Sie müssen Führungsqualitäten entwickeln und unabhängig handeln, indem Sie Ihre einzigartigen Talente zeigen. Tatsache ist, dass Menschen mit der Geisteszahl 7 eine einzigartige Sicht auf die Welt haben und geniale Dinge erschaffen können, aber oft von Zweifeln und Unentschlossenheit geplagt werden. Um alle Zweifel zu zerstreuen, ist es notwendig, Zeit für Sport und Konzentration des Geistes durch Meditation aufzuwenden.""",

    8: """Bedeutung des Geburtstages 8 Sie haben die produktivste Energie, die Sie ständig zur Arbeit motiviert. Sie müssen lernen, sich richtig auszuruhen und sich Ziele zu setzen, damit Ihre Arbeit auf Ergebnisse ausgerichtet ist. Ihr Streben, alles an sich zu reißen, kann Sie zu Gesetzesverstößen führen, daher lenken Sie Ihre Energie auf das Schaffen, nicht auf das Zerstören.
Geborene am 8. geboren sind, kommen ins Leben anderer Menschen, um deren Karma zu verändern. Deshalb durchlaufen sie in der ersten Hälfte ihres Lebens schwierige Prüfungen. Die gewonnene Erfahrung wird es Ihnen in Zukunft ermöglichen, die materielle Welt zu kontrollieren und andere Menschen zu lenken (durch sanfte Transformation oder durch Krisen). Für Sie ist es sehr wichtig, zu lernen, in Partnerschaft zu arbeiten und Ihre Aufgaben an andere Menschen zu delegieren, denn dadurch erweitern sich Ihre Ressourcen.""",

    9: """Bedeutung des Geburtstages 9 Ihre Hilfe kennt keine Grenzen, aber Sie müssen lernen, diese Grenzen zu setzen, um in Zukunft nicht auf Menschen beleidigt zu sein, weil man Sie unterschätzt hat. Lernen Sie, alle Kooperationsbedingungen "an Land" zu besprechen, weil andere Menschen nicht immer in der Lage sind, Ihre Arbeit angemessen zu würdigen.
Es ist sehr wichtig für Sie, ständig Neues zu lernen, weil Lernen Sie immer zum Erfolg führt und Ihre Energie beruhigt. Auch wird Ihnen empfohlen, sich mit Kreativität zu beschäftigen, damit Sie Ihre starke psychische Energie ausdrücken können. Wenn diese Energie keinen Ausdruck findet, können bei Ihnen innere Spannungen oder seelische Schwierigkeiten entstehen. Für Männer, die am 9. geboren sind, wird empfohlen, Sport zu treiben, insbesondere Kampfkunst, weil Sie mit der Energie des Mars im Bewusstsein geboren wurden.""",

    10: """Bedeutung des Geburtstages 10 Von Geburt an befindet sich in Ihrer Psyche ein Zustand der Unzufriedenheit mit sich selbst und mit Ihrer Umgebung. Sie müssen unbedingt an Ihrer Einstellung zum Leben arbeiten und eine positive Denkweise entwickeln. In diesem Fall werden Sie außergewöhnliche Ergebnisse erzielen und Ihre volle Verwirklichung erreichen!
Menschen, die am 10. Tag geboren sind, gelten als die energiereichsten Führungspersönlichkeiten. Nicht alle in ihrer Umgebung können ein so hohes Energieniveau richtig wahrnehmen – oft sind Sie viel zielstrebiger als andere, sind aber zugleich stärker von der Energie der Abwertung betroffen. Das bedeutet, dass Sie zwar schnell neue Projekte beginnen können, diese jedoch häufig nicht bis zum Ende durchziehen. Sie müssen unbedingt lernen, alle Ihre Vorhaben zu Ende zu bringen, um Ihr eigenes Ergebnis nicht zu entwerten.""",

    11: """Bedeutung des Geburtstages 11 Obwohl Sie ein guter Ratgeber und Helfer sind, sind Ihre Führungsqualitäten sehr stark ausgeprägt. Sie müssen ein Gleichgewicht finden zwischen dem Wunsch zu helfen und dem Drang, Ihre eigene Meinung durchzusetzen.
Im positiven Zustand können Sie in sich die Eigenschaften eines Führers und eines verständnisvollen Diplomaten vereinen. Das bedeutet, dass Sie in der Lage sind, große Gruppen von Menschen zu einen – und das hilft Ihnen, schneller zum Erfolg zu gelangen.
Doch oft leiden Menschen mit zwei Einsen unter dem Wunsch, Beziehungen aufzubauen, und der Unfähigkeit, dies zu verwirklichen, da ihr Bewusstsein zur Einsamkeit neigt. Lernen Sie, andere Menschen zu beschützen und zu unterstützen, indem Sie Ihre Initiative einsetzen.""",

    12: """Bedeutung des Geburtstages 12 Sie teilen die Welt in Dumme und Kluge ein und sind überzeugt, dass Sie viel mehr wissen als andere. Das hindert Sie daran, andere Menschen zu verstehen, was zu Konflikten und Streitigkeiten führt.
Befindet sich Ihr Bewusstsein im Positiven, können Sie ein hervorragender Manager werden, der durch Verständnis handelt.
Für Menschen, die am 12. Tag geboren sind, erweist sich dies oft als zu schmerzhaft und „krisenhaft“, was ihre Kommunikation mit anderen Menschen erschwert. Sie müssen Ihre Fähigkeiten zur Empathie und zum Verständnis anderer entwickeln, um nicht ins Negative abzurutschen.
Sie sollen ein Leitstern für andere Menschen werden, dabei aber ein einfühlsamer und verständnisvoller Freund für alle bleiben. Das ist möglich durch die Analyse Ihrer eigenen Absichten und die Entwicklung von Kommunikationsfähigkeiten, wobei Ihr Bewusstsein stets auf Hilfe und Dienst am Menschen ausgerichtet sein sollte.""",

    13: """Bedeutung des Geburtstages 13 Ihr häufigster Satz lautet: „Ich weiß!“ Sie wollen andere Menschen nicht anhören oder verstehen, weil Sie sich für den Klügsten halten. Gleichzeitig kann Ihr Bewusstsein unter ständiger Unzufriedenheit mit sich selbst und anderen Menschen leiden.
Entwickeln Sie Ihr Verständnis: Hören Sie anderen Menschen mehr zu und beraten Sie sich mit ihnen in wichtigen Fragen. Bemühen Sie sich, keine kritischen Urteile über andere zu fällen, bevor Sie die Situation vollständig verstanden haben.
Sie müssen lernen, Liebe und Fürsorge gegenüber anderen Menschen zu zeigen. Selbst wenn es Ihnen so vorkommt, dass Ihr Herz enttäuscht ist und andere Menschen Ihrer Liebe nicht würdig sind, werden Sie wahres Glück erfahren, wenn Sie in die positive Phase der Kreativität und der Liebe übergehen.""",

    14: """Bedeutung des Geburtstages 14 Sie sind ein autonomer Mensch, der in der Lage ist, selbst Initiative zu ergreifen und Neues zu schaffen und das eigene Produkt zu erweitern. Sie sind ein sehr effektiver Mensch, solange Sie nicht anfangen, sich über andere Menschen zu ärgern. Wir empfehlen Ihnen, aus dem Zustand der emotionalen Zerstörung herauszukommen, indem Sie positives Denken entwickeln.
Für Sie ist es wichtig, Anerkennung für Ihre Bemühungen zu erhalten und ständig positive Bestätigung für Ihre Handlungen zu finden. Am besten verwirklichen Sie sich in kreativen Bereichen. Um Ihren mentalen Zustand zu verbessern, wird Ihnen empfohlen, viel Zeit für Sport und körperliche Disziplin aufzuwenden, da diese Praktiken Ihren Geist schnell in einen Zustand der Genialität und Inspiration versetzen. Wenn Sie Ihrem Körper keine Aufmerksamkeit schenken, werden Sie häufiger auf Trübsinn, Enttäuschungen und emotionale Zusammenbrüche in Ihrem Leben stoßen.""",

    15: """Bedeutung des Geburtstages 15 Sie erreichen Ihre Ziele durch Initiative und Kommunikation. Sie können sehr hohe Ergebnisse im Business erzielen, indem Sie Ihre Weisheit nutzen und Angemessenheit. Ihre Schwäche ist die Neigung zu Verletzungen und übermäßigem Egoismus. Entwickeln Sie Verständnis für andere Menschen und bauen Sie effektive Kommunikation auf.
Sie können ein hervorragender Manager und Unternehmer werden, weil Sie in der Lage sind, mit verschiedenen Menschen eine gemeinsame Basis zu finden. Gleichzeitig besitzen Sie ein hohes Maß an Initiative. Probleme können entstehen, wenn Sie sich von augenblicklichen Begierden leiten lassen. Die Energie der Geisteszahl 6 prüft Sie ständig auf Ihre Beständigkeit gegenüber Versuchungen, daher müssen Sie in Reinheit bleiben, um Ihren Erfolg zu bewahren.""",

    16: """Bedeutung des Geburtstages 16 Die wichtigste Aufgabe für Sie ist es, zu lernen, Ihre Angelegenheiten durch Disziplin zu kontrollieren und nicht in die ständige Suche nach Vergnügungen abzugleiten. Das Leben wird Ihnen Liebe, Geld und Wohlstand schenken, wenn Sie alle Ihre Angelegenheiten in Ordnung bringen und lernen, Ihre Zeit zu kontrollieren.
Geborene am 16. geboren sind, wird die Energie ihres Bewusstseins immer durch Versuchungen und schädliche Neigungen prüfen. Jede Askese stärkt Sie, aber Sie müssen Willenskraft und Unverwundbarkeit gegenüber Ihren eigenen Wünschen entwickeln. Auch ist es sehr wichtig für Sie, zu lernen, jeden Ihrer Tage zu planen, langfristige Ziele zu setzen und alle Ihre Angelegenheiten zu Ende zu bringen. Dies wird Ihre Persönlichkeit stärker und größer machen.""",

    17: """Bedeutung des Geburtstages 17 Der beste Weg zur Verwirklichung für Sie ist die Bühne oder das Showbusiness. Sie sind in der Lage, sehr viel zu arbeiten, und dabei sucht Ihr Ego nach Anerkennung. Je tiefer Sie in den Prozess eintauchen, desto mehr Ruhm, Geld und Möglichkeiten werden Sie täglich erhalten.
Regelmäßiger Sport und die richtige Zielsetzung machen Sie stärker. Ihre chaotische Energie konzentriert sich, wodurch Sie Ergebnisse schneller erreichen. Hüten Sie sich vor extremem Verhalten (schnelles Fahren, Bewusstseinsveränderung), denn Ihre starke Energie kann Krisen in Ihrem Leben verursachen. Es ist wichtig, das Thema Beziehungen und Partnerschaft zu bearbeiten, denn Ihre Energie verwirklicht sich in der gemeinsamen Arbeit mit anderen Menschen.""",

    18: """Bedeutung des Geburtstages 18 Obwohl Sie ein sehr fleißiger Mensch sind (und oft ein Einzelgänger), müssen Sie lernen, sich Ziele zu setzen und Energie durch Sport zu generieren, damit all Ihre Handlungen sinnvoll sind und Sie zum Ergebnis führen. Nutzen Sie Ihre hohe Arbeitsfähigkeit mit Verstand und beschäftigen Sie sich nicht mit überflüssigen Dingen.
Als ausgezeichneter Helfer und sehr produktiver Mensch streben Sie danach, alles selbst zu machen. Ihre wahre Aufgabe ist es, zu lernen, durch Partnerschaft zu arbeiten und überhaupt das Thema Beziehungen in Ihrem Leben zu bearbeiten. Nur durch Beziehungen und Teamarbeit wachsen Sie wirklich und erreichen hohe Ergebnisse.""",

    19: """Bedeutung des Geburtstages 19 Sie sind ein feuriger Führer. In Ihrem Bewusstsein sind die stärksten Führungsqualitäten ausgeprägt. Sie sind fähig, Unglaubliches zu erschaffen, haben jedoch auch eine Neigung zur Zerstörung. Es ist für Sie unbedingt notwendig, sich durch Hilfe für andere zu verwirklichen und Ihr Ziel unbeirrt zu verfolgen.
Um aus einem Zustand der Streitlust herauszukommen, wird Ihnen empfohlen, sich ständig mit neuen Dingen zu beschäftigen. Lernen macht Ihre Energie harmonischer und nimmt Ihnen jene Naivität, die durch die Energie der Zahl 9 entsteht.
Zugleich streben Sie ständig danach, anderen Menschen zu dienen und ihnen Hilfe zu leisten, geraten dadurch jedoch selbst oft in problematische Situationen. Sie sollten Ihre Führungsenergie richtig einsetzen – immer durch kühlen Kopf, Analyse.""",

    20: """Bedeutung des Geburtstages 20 Nicht selten wird Ihnen ein „zerstörerischer Heiratscode“ zugeschrieben. Möglicherweise hatten Sie bereits mehrere Scheidungen.
Ihr Bewusstsein driftet sehr oft ins Negative ab, wenn Sie aufhören, Ihren Partner, eine Situation oder einen Arbeitsprozess zu verstehen. Sie müssen unbedingt ein positives Denken entwickeln und in jeder Situation nur die positiven Seiten sehen.
Im positiven Zustand können Sie ein sehr energiereicher Mensch mit offenem Herzen sein. In diesem Fall sind Sie bereit, an Ihren Beziehungen zu arbeiten und mehr Kraft in deren Stärkung zu investieren.
Wenn Sie Ihre Kommunikationsfähigkeiten entwickeln und lernen, die Prozesse, mit denen Sie sich beschäftigen, im Detail zu verstehen, werden Sie zum besten Umsetzer. Gleichzeitig ist es für Sie wichtig, sich in jeder Aufgabe in Partnerschaft mit anderen Menschen weiterzuentwickeln.""",

    21: """Bedeutung des Geburtstages 21 Obwohl Sie ein Mensch des Wissens sind, neigen Sie dazu, Ihre Fähigkeiten und Möglichkeiten zu unterschätzen und die Verantwortung auf andere Menschen – auf Mentoren – zu übertragen. Gleichzeitig haben Sie ein inneres Verständnis davon, was Sie erreichen möchten, handeln jedoch über andere, indem Sie diese durch Ihr Wissen beeinflussen.
Entwickeln Sie Zielstrebigkeit und lernen Sie, Verantwortung selbst zu übernehmen – unter Berücksichtigung Ihres Wissens über die Welt.
Sie sind ein einfühlsamer und sanfter Mensch, für den das Thema Beziehungen von großer Bedeutung ist. Wenn Ihre Beziehungen in Ordnung sind, fühlen auch Sie sich wohl. Sie sind ausdauernder und lernfähiger, was ebenfalls ein wichtiger Wachstumspunkt für Sie ist.
Durch Ihre sanfte und gütige Energie sind Sie in der Lage, Menschen richtig anzuleiten und ihnen mit Ihrem Wissen zu helfen.""",

    22: """Bedeutung des Geburtstages 22 Ihr Bewusstsein strebt ständig danach, Neues zu erschaffen, doch Sie führen begonnene Aufgaben oft nicht zu Ende. Sie neigen dazu, Verantwortung auf andere Menschen abzuwälzen.
Ihre optimale Verwirklichung liegt in Beziehungen. Wenn Sie Ihren Partner vollständig verstehen, können Sie ein hervorragender Helfer und Diplomat sein – vorausgesetzt, Sie verlassen den negativen Geisteszustand.
Oft werden Menschen mit diesem Geburtsdatum zu den besten Psychologen und Unterstützern in schwierigen Angelegenheiten. Ihre fleißige Energie ist in der Lage, die kreativsten Lösungen zu finden, insbesondere in Bereichen, die mit Beziehungen zu tun haben.""",

    23: """Bedeutung des Geburtstages 23 Sie verwirklichen sich hervorragend im Bereich Finanzen und Management. Durch ein tiefes Verständnis von Prozessen können Sie auch wichtiges Wissen über Business und Beziehungen an andere Menschen weitergeben und so Ihre Kommunikation entwickeln. Denken Sie daran, dass Ihnen in allen Angelegenheiten Glück beschieden ist, wenn Ihr Geist positiv und diszipliniert ist.
Indem Sie anderen Menschen Hilfe und Fürsorge entgegenbringen, verwirklichen Sie Ihre Energie optimal. Sie können der beste Mitarbeiter und Lehrer sein. Ihre Angemessenheit und kühle Berechnung helfen dabei, komplexe Aufgaben zu lösen, die einen klaren Verstand erfordern. Die Kehrseite dieser Energie ist Empfindsamkeit (aufgrund ständiger Zweifel) und List. Indem Sie Wärme und Hilfsbereitschaft gegenüber anderen Menschen zeigen, wachsen Sie als Persönlichkeit.""",

    24: """Bedeutung des Geburtstages 24 Durch ein tiefes Verständnis der Prozesse und den Drang, Neues zu schaffen, sind Sie in der Lage, ein Produkt zu erschaffen, das die Welt verändern wird. Es ist wichtig, sich nicht über andere Menschen zu ärgern, wenn Sie die Motivation ihrer Handlungen nicht verstehen können. Konzentrieren Sie sich auf Ihre Projekte und Aufgaben, die Ihnen vom Schöpfer gegeben wurden.
Es ist wichtig, die Fähigkeit zur Planung und Zielsetzung zu entwickeln, obwohl Sie diese Fähigkeit bereits von Geburt an besitzen. Auch das Steigern der Energie durch Sport und Meditation hilft Ihnen, gute Laune zu bewahren und auftretende Probleme schnell zu lösen. Wenn in Ihrem Leben regelmäßiger Sport fehlt, wird Ihr Bewusstsein in Negativität und Zerstörung abgleiten.""",

    25: """Bedeutung des Geburtstages 25 Ihre Stärken sind die Geschäftsentwicklung und Kommunikation durch das Verständnis von Menschen. Sie streben ständig danach, andere zu verstehen, und verwirklichen sich hervorragend in der Kommunikation. Täglicher Sport und die richtige Zielsetzung werden Ihnen in allen Angelegenheiten überragende Ergebnisse bringen.
Solche Menschen können zu List und Lügen neigen, und manchmal zwingt die Energie der 7 sie, sich ohne besonderen Grund so zu verhalten. Es ist wichtig, innere Ehrlichkeit zu entwickeln und zu lernen, Verpflichtungen und Verantwortung zu übernehmen. In diesem Fall werden Sie ein genialer Führer, der andere Menschen versteht. Sie haben ausgezeichnete Verhandlungsfähigkeiten, aber es ist wichtig für Sie, Ihre Aufmerksamkeit auf das Ergebnis zu konzentrieren.""",

    26: """Bedeutung des Geburtstages 26 Obwohl Ihre Bestimmung Arbeit, Kontrolle und Ergebnis ist, sucht Ihr Ego ständig nach Genuss. Man kann sagen, dass Sie innerlich sehr reich sind, auch wenn Sie überhaupt kein Geld haben. Lernen Sie, finanzielle Ziele durch Verständnis und Streben nach Erfolg zu setzen, entwickeln Sie Disziplin des Geistes und treiben Sie Sport.
Am 26. werden kreative Menschen mit einer reichen spirituellen Welt geboren. Manchmal erschafft diese Energie der Liebe und Weisheit Schwierigkeiten, weil Ihr Ego in allem nach Genuss sucht. Es ist notwendig, Selbstkontrolle und Disziplin zu entwickeln, damit Ihr reales Niveau Ihren hohen inneren Standards entspricht. In diesem Fall beherrschen Sie die materielle Welt, erreichen aber gleichzeitig Harmonie auf der spirituellen Ebene.""",

    27: """Bedeutung des Geburtstages 27 Ihre Stärke ist das tiefe Verständnis anderer Menschen und die Energie in Ihren Handlungen. Dabei wollen Sie ständig Anerkennung erhalten und leiden, wenn jemand Ihre Hilfe und Ihre Qualitäten nicht angemessen gewürdigt hat. Richten Sie Ihre Energie auf die Hilfe für Menschen, entwickeln Sie in sich Aufrichtigkeit und lernen Sie, selbstständig zu handeln, ohne Verantwortung auf andere Menschen abzuwälzen.
Geborene am 27. haben eine Leidenschaft für spirituelle Suche. Oft verneinen solche Menschen einfach die materielle Welt oder leben im Chaos, da die Energie der Zahlen 2 und 7 viele Zweifel und eine Loslösung von der realen Welt schafft. Ihre wirkliche Aufgabe ist es, sich in Partnerschaft mit anderen Menschen weiterzuentwickeln und komplexe Aufgaben zu lösen. Das ist Ihre Art, der Welt zu dienen.""",

    28: """Bedeutung des Geburtstages 28 Ihr Bewusstsein verwirklicht sich durch ein tiefes Verständnis von Managementprozessen. Sie sind fähig, sehr viel zu arbeiten und geniale Systeme zu erschaffen, indem Sie den gesamten Prozess steuern und kontrollieren. Sie sollten sich nicht von Kränkungen oder Erwartungen anderer Menschen leiten lassen – handeln Sie selbständig. Das ist der Schlüssel zu Ihrem Erfolg!
Menschen, die am 28. Tag geboren sind, werden oft Eigentümer großer Unternehmen (z. B. Bill Gates, Elon Musk) oder talentierte Fachkräfte in anderen Bereichen. Doch um dieses geniale Potential voll zu entfalten, ist es notwendig, die Fähigkeit zum Verständnis und Zuhören mit dem Wunsch nach Kontrolle zu verbinden.
Durch den Aufbau großer Strukturen und Teams gelangen Menschen mit diesem Geburtsdatum zum größten Erfolg.""",

    29: """Bedeutung des Geburtstages 29 Menschen, die an diesem Datum geboren sind, besitzen ein großes energetisches Potential von Mond und Mars. Sie können Ihre Bestimmung in der Hilfe für andere Menschen finden. Niemand kann diese Aufgabe besser erfüllen als Sie. Solche Menschen sind fähig, sich im spirituellen Bereich zu entwickeln und richten ihre Aufmerksamkeit auf den Dienst an der Menschheit – sofern sie sich in einem positiven Geisteszustand befinden.
Befinden Sie sich jedoch in einer „negativen Phase“, neigen Sie zu Intrigen und geheimen Verbindungen, die zur Zerstörung führen. Diese Zerstörung wirkt sich in erster Linie negativ auf Ihr Schicksal aus. Genau deshalb sollte Ihre gesamte Aufmerksamkeit auf die Hilfe und das Verständnis für andere Menschen gerichtet sein. Darin liegt Ihre maximale Verwirklichung.""",

    30: """Bedeutung des Geburtstages 30 Sie sind ein "ziemlich" listiger Mensch, der das Wissen anderer Menschen zunichtemacht. Dabei können Sie selbst sehr oft dumme oder unüberlegte Handlungen begehen, die negative Reaktionen anderer Menschen hervorrufen. Sie müssen unbedingt positives Denken entwickeln und Ihr eigenes Wissen über die Welt festigen, das Ihnen die Möglichkeit gibt, Ihre Ziele sehr schnell zu erreichen.
Oft faulenzen Menschen, die am 30. geboren sind, bei ihrer Selbstbildung und sind nicht zum Lesen von Literatur geneigt. Aber tatsächlich ist die Steigerung Ihrer Allgemeinbildung der beste Weg, um schnell Erfolg zu haben. Im Idealfall sollten Sie Spezialist in mehreren Bereichen gleichzeitig werden. Dann werden Sie den Gegenstand viel besser verstehen als andere Menschen, und Ihre stürmische Energie wird Ihnen helfen, Ziele schneller zu erreichen.""",

    31: """Bedeutung des Geburtstages 31 Sie sind ein Mensch mit großem Verstand und hervorragenden Führungsqualitäten. Diese Eigenschaft kann Ihnen sehr schnell Resultate bringen, kann jedoch auch zur Ursache von Zerstörung werden. Über Sie sagt man: „Unglück durch zu viel Verstand“. Sie wissen alles, wollen jedoch andere Menschen nicht verstehen – und genau dieses Hindernis müssen Sie in sich überwinden.
Menschen, die an diesem Tag geboren sind, haben eine globale Bestimmung, die manchmal schwer zu begreifen und zu erkennen ist. Mit Hilfe Ihres Intellekts und Ihrer Führungsqualitäten müssen Sie globale und kreative Projekte erschaffen. Doch Ihr Bewusstsein sollte dabei auf Liebe und Dienst an den Menschen ausgerichtet sein. Nur in diesem Fall können sich Ihre genialen Ideen wirklich verwirklichen und der ganzen Welt großen Nutzen bringen.""" 
}


# -*- coding: utf-8 -*-
import os, re
from datetime import datetime
from typing import Tuple, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters
)
from dotenv import load_dotenv



# ========================= API TOKEN =========================
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
if not API_TOKEN:
    raise SystemExit("API_TOKEN is missing. Set it in env.")
# =============================================================

# ----------------------------- Utils -----------------------------
def html_escape(s: str) -> str:
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def parse_date(text: str) -> Tuple[int,int,int]:
    m = re.search(r'(\d{1,2})[.\s](\d{1,2})[.\s](\d{4})', text)
    if not m:
        raise ValueError("Bitte Datum im Format TT.MM.JJJJ, z. B. 25.11.1978.")
    d, mth, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
    datetime(year=yr, month=mth, day=d)  # validate
    return d, mth, yr

def parse_dates_multi(text: str) -> List[Tuple[int,int,int]]:
    found = re.findall(r'(\d{1,2})[.\s](\d{1,2})[.\s](\d{4})', text)
    result = []
    for d, mth, yr in found:
        day, month, year = int(d), int(mth), int(yr)
        datetime(year=year, month=month, day=day)
        result.append((day, month, year))
    return result

def reduzieren(n: int, keep_master=True) -> int:
    while n > 9:
        s = sum(int(d) for d in str(n))
        if keep_master and s in (11, 22, 33):
            return s
        n = s
    return n

def reduzieren_1_9(n: int) -> int:
    while n > 9:
        n = sum(int(d) for d in str(n))
    return n

# ------------------------- Формулы -----------------------
def geisteszahl(day: int) -> int: return reduzieren(day)
def handlungszahl(day: int, month: int, year: int) -> int: return reduzieren(sum(int(d) for d in f"{day:02d}{month:02d}{year}"))
def verwirklichungszahl(g: int, h: int) -> int: return reduzieren(g + h)
def ergebniszahl(g: int, h: int, v: int) -> int: return reduzieren(g + h + v)
def geldcode(day: int, month: int, year: int) -> str:
    d1, d2 = reduzieren(day), reduzieren(month)
    d3 = reduzieren(sum(int(d) for d in str(year)))
    d4 = reduzieren(d1 + d2 + d3)
    return f"{d1}{d2}{d3}{d4}"
def tagesenergie(bday_day: int, today_day: int) -> int: return reduzieren_1_9(sum(int(d) for d in f"{bday_day:02d}{today_day:02d}"))

# ----------------------------- Меню/состояния ------------------------------
ASK_DAY_BIRTH, ASK_COMPAT_1, ASK_COMPAT_2, ASK_NAME, ASK_GROUP, ASK_FULL, ASK_PATH = range(7)

WELCOME = ("🌟 <b>Willkommen!</b>\n\n"
"Vor Ihnen liegt <b>KeyToFate</b> – Lehre über Zahlen und Wege.\n\n"
"✨ Lüften Sie den Schleier Ihres Schicksals – und lassen Sie KeyToFate Ihr Wegweiser sein. ✨")
MENU_HEADER = "🔽 <b>Hauptmenü</b>\nBitte wählen Sie:"

def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧮 Vollanalyse", callback_data="calc_full")],
        [InlineKeyboardButton("🔆 Tagesenergie", callback_data="calc_day")],
        [InlineKeyboardButton("💞 Partnerschaft", callback_data="calc_compat")],
        [InlineKeyboardButton("🔤 Namensenergie", callback_data="calc_name")],
        [InlineKeyboardButton("👥 Kollektivenergie", callback_data="calc_group")],
        [InlineKeyboardButton("🧭 Entwicklungspfad", callback_data="calc_path")],
    ])

# ---- Handlers ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("➡️ Zum Menü", callback_data="open_menu")]])
    await update.message.reply_html(WELCOME, reply_markup=kb)

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await q.message.reply_html(MENU_HEADER, reply_markup=main_menu())
    return ConversationHandler.END

async def on_menu_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; data = q.data; await q.answer()
    if data=="calc_full":
        await q.message.reply_html("🧮 Geben Sie Geburtsdatum ein (TT.MM.JJJJ):"); return ASK_FULL
    if data=="calc_day":
        await q.message.reply_html("Geben Sie Ihr Geburtsdatum ein (TT.MM.JJJJ):"); return ASK_DAY_BIRTH
    if data=="calc_compat":
        await q.message.reply_html("Geben Sie Geburtsdatum Person 1 ein (TT.MM.JJJJ):"); return ASK_COMPAT_1
    if data=="calc_name":
        await q.message.reply_html("Geben Sie den Namen ein (lateinische Schreibweise):"); return ASK_NAME
    if data=="calc_group":
        context.user_data["group_birthdays"] = []
        await q.message.reply_html("👥 Bis zu 5 Geburtstage eingeben. Schreiben Sie <b>fertig</b>, wenn bereit."); return ASK_GROUP
    if data=="calc_path":
        await q.message.reply_html("🧭 Bitte Geburtsdatum eingeben (TT.MM.JJJJ):"); return ASK_PATH
    return ConversationHandler.END

# ---- Vollanalyse ----
async def ask_full(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        d,m,y = parse_date(update.message.text.strip())
        g,h = geisteszahl(d), handlungszahl(d,m,y)
        v,e = verwirklichungszahl(g,h), ergebniszahl(g,h,v)
        geld = geldcode(d,m,y)

        geist_short = GEISTES_TXT.get(g,"")
        geist_full  = get_geistes(g)
        handl_full  = get_handlungs(h)
        verw_full   = get_verwirk(v)
        erg_full    = get_ergebnis(e)

        day_text = (DAY_BIRTH_TXT.get(d) or "").strip()
        day_block = f"\n\n📅 <b>Bedeutung des Geburtstagstages {d}</b>\n{html_escape(day_text)}" if day_text else ""

        parts = [
            f"<b>Vollanalyse für {d:02d}.{m:02d}.{y}</b>",
            f"🧠 <b>Geisteszahl {g}</b>\n{html_escape(geist_short)}",
        ]
        if geist_full: parts.append(html_escape(geist_full))
        parts.append(f"\n⚡ <b>Handlungszahl {h}</b>\n{HANDLUNG_SHORT[(h-1)%9]}")
        if handl_full: parts.append(html_escape(handl_full))
        parts.append(f"\n🎯 <b>Verwirklichungszahl {v}</b>\n{VERWIRK_SHORT[(v-1)%9]}")
        if verw_full: parts.append(html_escape(verw_full))
        parts.append(f"\n📘 <b>Ergebniszahl {e}</b>\n{ERGEBNIS_SHORT[(e-1)%9]}")
        if erg_full: parts.append(html_escape(erg_full))
        parts.append(f"\n💰 <b>Geldcode:</b> <code>{geld}</code>")
        if day_block: parts.append(day_block)

        await update.message.reply_html("\n\n".join(parts))
        return ConversationHandler.END
    except Exception as ex:
        await update.message.reply_html(f"❌ Fehler: {html_escape(str(ex))}"); return ASK_FULL

# ---- Tagesenergie ----
async def ask_day_birth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        d,m,y = parse_date(update.message.text.strip()); today = datetime.now()
        val = tagesenergie(d, today.day)
        body = TAG_TXT.get(val, "Energie im Fluss.")
        await update.message.reply_html(
            f"📅 <b>Tagesenergie {today.day:02d}.{today.month:02d}.{today.year}</b>\n\n{html_escape(body)}"
        )
        return ConversationHandler.END
    except Exception as ex:
        await update.message.reply_html(f"❌ {html_escape(str(ex))}"); return ASK_DAY_BIRTH

# ---- Partnerschaft ---- (из книги)
async def ask_compat1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d1,m1,y1 = parse_date(update.message.text.strip())
    context.user_data["compat1"]=(d1,m1,y1,update.message.text.strip())
    await update.message.reply_html("Jetzt <b>Geburtsdatum Person 2</b> eingeben (TT.MM.JJJJ):"); return ASK_COMPAT_2

async def ask_compat2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d2,m2,y2 = parse_date(update.message.text.strip())
    d1,m1,y1,s1 = context.user_data.get("compat1")
    g1,g2 = geisteszahl(d1), geisteszahl(d2)
    common = reduzieren_1_9(g1 + g2)
    long_txt = get_partner(common)
    header = (
        "💞 <b>Partnerschaft</b>\n\n"
        f"<b>Person 1:</b> {s1} → Geisteszahl {g1}\n"
        f"<b>Person 2:</b> {update.message.text.strip()} → Geisteszahl {g2}\n\n"
    )
    body = html_escape(long_txt) if long_txt else f"(Gemeinsame Geisteszahl {common})"
    await update.message.reply_html(header + body)
    context.user_data.pop("compat1", None)
    return ConversationHandler.END

# ---- Namensenergie ----
NAME_MAP = {
    **{c:1 for c in "AIJQY"}, **{c:2 for c in "BKR"}, **{c:3 for c in "CLSG"},
    **{c:4 for c in "DMT"}, **{c:5 for c in "EHNX"}, **{c:6 for c in "UVW"},
    **{c:7 for c in "OZ"}, **{c:8 for c in "FP"},
}
def normalize_latin(s: str) -> str:
    return (s.replace("Ä","A").replace("Ö","O").replace("Ü","U")
              .replace("ä","a").replace("ö","o").replace("ü","u")
              .replace("ß","SS"))
def namensenergie(text: str) -> int:
    vals = [NAME_MAP[ch] for ch in normalize_latin(text).upper() if ch in NAME_MAP]
    return reduzieren(sum(vals)) if vals else 0

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name=update.message.text.strip(); val=namensenergie(name)
    await update.message.reply_html(f"🔤 <b>Namensenergie</b> „{html_escape(name)}“: <b>{val}</b>")
    return ConversationHandler.END

# ---- Kollektivenergie ---- (без Entwicklungspfад)
async def ask_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text=(update.message.text or "").strip()
    if text.lower()=="fertig":
        group=context.user_data.get("group_birthdays",[])
        if len(group)<2:
            await update.message.reply_html("❌ Mindestens 2 Personen."); return ASK_GROUP
        geistes_list=[geisteszahl(d) for d,_,_ in group]
        kollektiv = reduzieren_1_9(sum(geistes_list))
        personen="\n".join(f"• {d:02d}.{m:02d}.{y} → Geisteszahl {g}" for (d,m,y),g in zip(group,geistes_list))
        txt = KOLLEKTIV_TXT.get(kollektiv, "Dieses Kollektiv entfaltet eine besondere Dynamik und Lernaufgabe.")
        await update.message.reply_html(f"👥 <b>Kollektivenergie</b>\n\n{personen}\n\n<b>Zahl:</b> {kollektiv}\n\n{html_escape(txt)}")
        return ConversationHandler.END
    parsed=parse_dates_multi(text)
    group=context.user_data.setdefault("group_birthdays",[])
    group.extend(parsed)
    await update.message.reply_html(f"✅ Hinzugefügt: {len(parsed)}. Tippen Sie <b>fertig</b>."); return ASK_GROUP

# ---- Entwicklungspfad ---- (индивидуальный)
ENTWICKLUNGSPFAD = {
    1: "Die 1 reift zur 4 — über Beziehung (2) und Ausdruck (3): aus Impuls werden Disziplin und Struktur.",
    2: "Die 2 strebt zur 5 — über Wissen/Kommunikation (3) и Ordnung (4): Harmonie wird zu bewusster Freiheit.",
    3: "Die 3 entfaltet sich zur 6 — über Struktur (4) und Wandel (5): Kreativität wird zu reifer Verantwortung.",
    4: "Die 4 wächst zur 7 — über Freiheit (5) und Liebe/Verantwortung (6): Ordnung wird zu innerer Weisheit.",
    5: "Die 5 strebt zur 8 — über 6 und 7: Liebe/Verantwortung → Wahrheit/Disziplin → gerechter Erfolg.",
    6: "Die 6 geht zur 9 — über Tiefgang (7) und Macht/Erfolg (8): zur universellen Liebe und zum Dienst.",
    7: "Die 7 geht zur 1 — über 8 und 9: Disziplin & Macht, dann Abschluss & Dienst hin zur reifen Führung.",
    8: "Die 8 strebt zur 2 — über 9 и 1: von Macht zu Kooperation und Diplomatie.",
    9: "Die 9 findet zur 3 — über 1 und 2: Dienst & Vollendung führen zu schöpferischem Ausdruck.",
}
ZU_VERMEIDEN = {
    1: "Ego-Alleingänge, Ungeduld, Dominanz.",
    2: "Unentschlossenheit, konfliktscheues Schweigen, Selbstverleugnung.",
    3: "Zerstreuung, zu viele Projekte, Oberflächlichkeit.",
    4: "Überstrenge Routinen, Dogmatismus, Detailkontrolle.",
    5: "Reizjagd, Hektik, Flucht in Abwechslung, Bindungsangst.",
    6: "Überverantwortung, Einmischung, subtile Schuldgefühle.",
    7: "Isolation, endloses Zweifeln, Theorie ohne Praxis.",
    8: "Machtspiele, Mikromanagement, Erfolgsfixierung.",
    9: "Selbstaufopferung, diffuse Ziele, Grenzenlosigkeit.",
}

async def ask_path(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d,m,y=parse_date(update.message.text.strip()); g=geisteszahl(d)
    out=(f"🧭 <b>Entwicklungspfad (aus Geisteszahl {g})</b>\n\n"
         f"{ENTWICKLUNGSPFAD.get(g,'')}\n\n"
         f"⚠️ <b>Zu vermeiden:</b> {ZU_VERMEIDEN.get(g,'')}")
    await update.message.reply_html(out); return ConversationHandler.END

# ---------------------------- Bootstrap ----------------------------
def main():
    app = Application.builder().token(API_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^open_menu$"))
    conv=ConversationHandler(
        entry_points=[CallbackQueryHandler(on_menu_click, pattern="^calc_")],
        states={
          ASK_FULL:[MessageHandler(filters.TEXT & ~filters.COMMAND, ask_full)],
          ASK_DAY_BIRTH:[MessageHandler(filters.TEXT & ~filters.COMMAND, ask_day_birth)],
          ASK_COMPAT_1:[MessageHandler(filters.TEXT & ~filters.COMMAND, ask_compat1)],
          ASK_COMPAT_2:[MessageHandler(filters.TEXT & ~filters.COMMAND, ask_compat2)],
          ASK_NAME:[MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
          ASK_GROUP:[MessageHandler(filters.TEXT & ~filters.COMMAND, ask_group)],
          ASK_PATH:[MessageHandler(filters.TEXT & ~filters.COMMAND, ask_path)],
        }, fallbacks=[CommandHandler("start", start)], allow_reentry=True
    )
    app.add_handler(conv)
    print("🤖 KeyToFate läuft. /start → Menü.")
    app.run_polling()

if __name__=="__main__":
    main()
