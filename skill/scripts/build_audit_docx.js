#!/usr/bin/env node
/**
 * Build the branded RankedTag audit .docx from audit.json (+ proof.json/assets).
 *
 * Usage:
 *   node build_audit_docx.js --data ./audit.json --assets ./assets_run --out ./rankedtag_audit_client.docx
 *
 * Requires: npm install docx  (run in the working dir)
 * Reads visuals + proof.json + logo_crop.png from --assets.
 */
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun,
  Footer, AlignmentType, LevelFormat, HeadingLevel, BorderStyle,
  WidthType, ShadingType, VerticalAlign, PageNumber, ExternalHyperlink,
} = require("docx");

/* ---- args ---- */
const args = Object.fromEntries(process.argv.slice(2).reduce((acc,cur,i,arr)=>{
  if(cur.startsWith("--")) acc.push([cur.slice(2), arr[i+1]]); return acc;
},[]));
const DATA = JSON.parse(fs.readFileSync(args.data,"utf8"));
const ASSETS = args.assets || ".";
const OUT = args.out || "rankedtag_audit.docx";
const proofPath = path.join(ASSETS,"proof.json");
const PROOF = fs.existsSync(proofPath) ? JSON.parse(fs.readFileSync(proofPath,"utf8")) : null;

/* ---- palette ---- */
const INK="161618",RED="FF3B14",RED_DK="C8260A",GREEN="2D8A5C",GREEN_DK="1F4D3F",
      AMBER="C97A06",PERI="6B77E0",MUTE="6E6E76",PAPER="F4EFE7",LINE="E0D7C7",
      WHITE="FFFFFF",REDTINT="FBEAE4",GREENTINT="E6F1EC",PERITINT="EEF0FB";
const FONT="Arial", CW=9360;
const CL = DATA.clientLabel || DATA.client;

/* ---- image helpers (auto-read dimensions) ---- */
function pngSize(file){ // minimal PNG/JPEG dimension reader
  const buf=fs.readFileSync(file);
  if(buf[0]===0x89&&buf[1]===0x50){ return [buf.readUInt32BE(16), buf.readUInt32BE(20)]; }
  // JPEG
  let o=2;
  while(o<buf.length){
    if(buf[o]!==0xFF){o++;continue;}
    const m=buf[o+1];
    if(m>=0xC0&&m<=0xCF&&m!==0xC4&&m!==0xC8&&m!==0xCC){
      return [buf.readUInt16BE(o+7), buf.readUInt16BE(o+5)];
    }
    o+=2+buf.readUInt16BE(o+2);
  }
  return [1000,1000];
}
const imgRun=(file,w)=>{
  const p=path.join(ASSETS,file); const [iw,ih]=pngSize(p);
  const h=Math.round(w*ih/iw);
  const type=/\.jpe?g$/i.test(file)?"jpg":"png";
  return new ImageRun({type,data:fs.readFileSync(p),transformation:{width:w,height:h},
    altText:{title:file,description:file,name:file}});
};
const imgPara=(file,w,{align=AlignmentType.CENTER,after=160,before=120}={})=>
  new Paragraph({alignment:align,spacing:{before,after},children:[imgRun(file,w)]});
const has=(file)=>fs.existsSync(path.join(ASSETS,file));

/* ---- text helpers ---- */
const t=(text,o={})=>new TextRun({text,size:21,color:INK,font:FONT,...o});
const b=(text,o={})=>new TextRun({text,size:21,color:INK,font:FONT,bold:true,...o});
const eyebrow=(txt,color=RED,{before=0,after=60}={})=>new Paragraph({spacing:{before,after},
  children:[new TextRun({text:txt.toUpperCase(),bold:true,color,size:18,font:FONT,characterSpacing:60})]});
const h1=(txt,{num=null}={})=>new Paragraph({heading:HeadingLevel.HEADING_1,spacing:{before:340,after:140},
  children:[...(num?[new TextRun({text:num+"  ",bold:true,color:RED,size:30,font:FONT})]:[]),
            new TextRun({text:txt,bold:true,color:INK,size:30,font:FONT})]});
const h2=(txt,color=INK)=>new Paragraph({heading:HeadingLevel.HEADING_2,spacing:{before:240,after:90},
  children:[new TextRun({text:txt,bold:true,color,size:24,font:FONT})]});
const body=(runs,{after=140,before=0,align=AlignmentType.LEFT}={})=>new Paragraph({alignment:align,
  spacing:{before,after,line:276},children:(typeof runs==="string"?[t(runs)]:runs)});
const bullet=(runs,{after=80}={})=>new Paragraph({numbering:{reference:"bullets",level:0},
  spacing:{after,line:272},children:(typeof runs==="string"?[t(runs)]:runs)});
const spacer=(h=120)=>new Paragraph({spacing:{after:h},children:[new TextRun("")]});
const ruleP=(color=LINE,size=8)=>new Paragraph({spacing:{before:60,after:120},
  border:{bottom:{style:BorderStyle.SINGLE,size,color,space:1}},children:[new TextRun("")]});

const callout=(label,runs,{fill=PERITINT,accent=PERI,labelColor=null}={})=>{
  const lc=labelColor||accent;
  return new Table({width:{size:CW,type:WidthType.DXA},columnWidths:[CW],rows:[
    new TableRow({children:[new TableCell({width:{size:CW,type:WidthType.DXA},
      shading:{fill,type:ShadingType.CLEAR},margins:{top:140,bottom:140,left:200,right:200},
      borders:{top:{style:BorderStyle.NONE},bottom:{style:BorderStyle.NONE},right:{style:BorderStyle.NONE},
        left:{style:BorderStyle.SINGLE,size:28,color:accent}},
      children:[
        new Paragraph({spacing:{after:40},children:[new TextRun({text:label.toUpperCase(),bold:true,color:lc,size:17,font:FONT,characterSpacing:50})]}),
        new Paragraph({spacing:{after:0,line:272},children:(typeof runs==="string"?[t(runs)]:runs)}),
      ]})]})]});
};

const band=(eyebrowTxt,title,sub,{titleSize=40}={})=>new Table({width:{size:CW,type:WidthType.DXA},columnWidths:[CW],rows:[
  new TableRow({children:[new TableCell({width:{size:CW,type:WidthType.DXA},shading:{fill:INK,type:ShadingType.CLEAR},
    margins:{top:340,bottom:340,left:340,right:340},
    borders:{top:{style:BorderStyle.NONE},bottom:{style:BorderStyle.NONE},left:{style:BorderStyle.NONE},right:{style:BorderStyle.NONE}},
    children:[
      new Paragraph({spacing:{after:100},children:[new TextRun({text:eyebrowTxt.toUpperCase(),bold:true,color:"A6B0F0",size:20,font:FONT,characterSpacing:90})]}),
      new Paragraph({spacing:{after:80},children:[new TextRun({text:title,bold:true,color:WHITE,size:titleSize,font:FONT})]}),
      ...(sub?[new Paragraph({children:[new TextRun({text:sub,color:"E6E1D8",size:23,font:FONT})]})]:[]),
    ]})]})]});

function makeTable(headers,rows,widths,{headFill=INK,zebra=PAPER}={}){
  const bd={style:BorderStyle.SINGLE,size:1,color:LINE};const borders={top:bd,bottom:bd,left:bd,right:bd};
  const headRow=new TableRow({tableHeader:true,children:headers.map((h,i)=>new TableCell({borders,
    width:{size:widths[i],type:WidthType.DXA},shading:{fill:headFill,type:ShadingType.CLEAR},
    margins:{top:90,bottom:90,left:130,right:130},verticalAlign:VerticalAlign.CENTER,
    children:[new Paragraph({children:[new TextRun({text:h,bold:true,color:WHITE,size:19,font:FONT})]})]}))});
  const dataRows=rows.map((r,ri)=>new TableRow({children:r.map((cell,ci)=>new TableCell({borders,
    width:{size:widths[ci],type:WidthType.DXA},shading:{fill:ri%2?zebra:WHITE,type:ShadingType.CLEAR},
    margins:{top:80,bottom:80,left:130,right:130},verticalAlign:VerticalAlign.CENTER,
    children:[new Paragraph({spacing:{line:264},children:Array.isArray(cell)?cell:[new TextRun({text:String(cell),size:19,color:INK,font:FONT})]})]}))}));
  return new Table({width:{size:CW,type:WidthType.DXA},columnWidths:widths,rows:[headRow,...dataRows]});
}
const paras=(arr)=>arr.map(p=>body(p));

/* ============ COVER ============ */
const cover=[
  ...(has("logo_crop.png")?[imgPara("logo_crop.png",190,{align:AlignmentType.LEFT,before:0,after:200})]:[spacer(40)]),
  band("SEO & AI-search audit", DATA.client, DATA.subtitle||"", {titleSize:76}),
  spacer(220),
  body([t("Prepared for ",{color:MUTE}),b(CL+" "),t(`(${DATA.client})${DATA.businessType?" — "+DATA.businessType:""}.`,{color:MUTE})],{after:60}),
  body([t("Prepared by ",{color:MUTE}),b(DATA.consultantName||"RankedTag"),t(" · RankedTag — the inbound engine for SaaS founders.",{color:MUTE})],{after:60}),
  body([t(DATA.date||new Date().toLocaleString("en-US",{month:"long",year:"numeric"}),{color:MUTE})],{after:0}),
  ruleP(LINE,6),
  body([b("Inside: "),t("why this matters now · how the site was assessed · the scorecard · what's costing you the most · a 30-day plan · the full action list · and proof of this exact engine in the wild for ",{color:MUTE}),
        t(PROOF?PROOF.client:"sendr.ai",{color:PERI,bold:true}),t(".",{color:MUTE})]),
];

/* ============ NOTE ============ */
const note=[
  new Paragraph({pageBreakBefore:true,children:[]}),
  eyebrow("A quick note before you dig in"),
  h1(`Hi ${CL} team —`),
  ...paras(DATA.note||[]),
  body([t("— "+(DATA.consultantFirstName||"The RankedTag team"),{italics:true,color:MUTE})],{before:60}),
];

/* ============ WHY ============ */
const why=DATA.why?[
  new Paragraph({pageBreakBefore:true,children:[]}),
  eyebrow("The why"),
  h1("Search just split into two races",{num:"1"}),
  ...paras(DATA.why.intro||[]),
  ...(DATA.why.callout?[callout(DATA.why.calloutLabel||`Why this matters for ${CL}`,DATA.why.callout,{fill:PERITINT,accent:PERI})]:[]),
  ...(DATA.why.outro?[body(DATA.why.outro,{before:140})]:[]),
]:[];

/* ============ METHOD + SCORECARD ============ */
const method=[
  new Paragraph({pageBreakBefore:true,children:[]}),
  eyebrow("The what & how"),
  h1("What I looked at, and how",{num:"2"}),
  ...(DATA.method?.scope?[body(DATA.method.scope)]:[]),
  ...(DATA.method?.how?[body([b("Method, in plain terms. "),t(DATA.method.how)])]:[]),
  h1("The scorecard",{num:"3"}),
  body("Schema and AI-search readiness are usually the two areas pulling the score down. Both are addressed directly in the plan that follows.",{after:60}),
  ...(has("viz_scorecard.png")?[imgPara("viz_scorecard.png",624),
    body([t("Read it like a dashboard: green is healthy, amber is fair-but-improvable, red needs attention. The lost points cluster in a handful of fixable themes.",{color:MUTE,size:19,italics:true})],{align:AlignmentType.CENTER})]:[]),
];

/* ============ CRITICAL ============ */
const visualFor=(v)=>{
  if(v==="richresult"&&has("viz_richresult.png")) return imgPara("viz_richresult.png",624,{after:60});
  if(v==="meta"&&has("viz_meta.png")) return imgPara("viz_meta.png",624,{after:60});
  return null;
};
const critical=[
  new Paragraph({pageBreakBefore:true,children:[]}),
  eyebrow("What's costing you the most",RED),
  h1("Fix these first",{num:"4"}),
  ...(DATA.critical||[]).flatMap(f=>[
    h2(f.heading,RED_DK),
    ...paras(f.body||[]),
    ...(visualFor(f.visual)?[visualFor(f.visual)]:[]),
    ...(f.whatToDo?[callout("What to do",f.whatToDo,{fill:GREENTINT,accent:GREEN,labelColor:GREEN_DK})]:[]),
  ]),
];

/* ============ HIGH ============ */
const high=(DATA.high&&DATA.high.length)?[
  new Paragraph({pageBreakBefore:true,children:[]}),
  eyebrow("High priority — within a week",AMBER),
  h1("The week-one list",{num:"5"}),
  ...(DATA.high||[]).flatMap(f=>[
    h2(f.heading),
    ...paras(f.body||[]),
    ...(visualFor(f.visual)?[visualFor(f.visual)]:[]),
    ...(f.whatToDo?[callout("What to do",f.whatToDo,{fill:GREENTINT,accent:GREEN,labelColor:GREEN_DK})]:[]),
  ]),
]:[];

/* ============ MEDIUM ============ */
const medium=(DATA.medium&&DATA.medium.length)?[
  spacer(160),
  eyebrow("Medium priority — within a month",GREEN_DK),
  h1("Worth doing this month",{num:"6"}),
  body("Lower urgency, still genuine value. Several are nearly free because the content already exists.",{after:120}),
  makeTable(["Finding","Why it matters / what to do"],
    DATA.medium.map(m=>[[b(m.finding,{size:19})], m.detail]),[3000,6360]),
]:[];

/* ============ QUICK WINS ============ */
const quick=(DATA.quickWins&&DATA.quickWins.length)?[
  new Paragraph({pageBreakBefore:true,children:[]}),
  eyebrow("Start here",RED),
  h1("Five quick wins",{num:"7"}),
  body("If the team can only touch a handful of things first, these return the most for the least effort. Ordered by estimated return.",{after:60}),
  ...DATA.quickWins.map(q=>bullet([b(q.title),t(" — "+q.detail)])),
  ...(has("viz_roadmap.png")?[spacer(80),imgPara("viz_roadmap.png",624)]:[]),
]:[];

/* ============ ACTION PLAN ============ */
const plan=(DATA.actionPlan&&DATA.actionPlan.length)?[
  new Paragraph({pageBreakBefore:true,children:[]}),
  eyebrow("The full list"),
  h1("Recommended action plan",{num:"8"}),
  body([t("Every recommendation, with a suggested owner and rough effort. Owners: "),b("Dev"),t(" = development, "),b("Content"),t(" = content / SEO, "),b("Marketing"),t(" = marketing.")],{after:120}),
  makeTable(["Action","Owner","Effort","Expected impact"],
    DATA.actionPlan.map(r=>[r.action,r.owner,r.effort,r.impact]),[4360,1200,1200,2600]),
]:[];

/* ============ COMPETITIVE ============ */
const comp=DATA.competitive?[
  new Paragraph({pageBreakBefore:true,children:[]}),
  eyebrow("Where you stand"),
  h1("Competitive context",{num:"9"}),
  ...(DATA.competitive.intro?[body(DATA.competitive.intro,{after:120})]:[]),
  ...(DATA.competitive.points||[]).map(p=>bullet(p)),
]:[];

/* ============ PROOF ============ */
let proof=[];
if(PROOF){
  const metricCell=(m,col)=>new TableCell({width:{size:3120,type:WidthType.DXA},
    shading:{fill:PAPER,type:ShadingType.CLEAR},margins:{top:160,bottom:160,left:120,right:120},
    borders:{top:{style:BorderStyle.SINGLE,size:1,color:LINE},bottom:{style:BorderStyle.SINGLE,size:1,color:LINE},
      left:{style:BorderStyle.SINGLE,size:1,color:LINE},right:{style:BorderStyle.SINGLE,size:1,color:LINE}},
    children:[
      new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:40},children:[new TextRun({text:m.big,bold:true,color:col,size:40,font:FONT})]}),
      new Paragraph({alignment:AlignmentType.CENTER,children:[new TextRun({text:m.small,color:MUTE,size:17,font:FONT})]}),
    ]});
  const cols=[INK,GREEN_DK,RED_DK];
  proof=[
    new Paragraph({pageBreakBefore:true,children:[]}),
    band("Proof — not promises", `What this exact engine did for ${PROOF.client}`, PROOF.stage?`${PROOF.stage}, competing against the category leaders, with no enterprise budget.`:""),
    spacer(160),
    body([t(`${CL} doesn't need to take my word for the plan above — here's the same playbook already in the wild. `),b(PROOF.client+" "),t(PROOF.intro)]),
    spacer(60),
    new Table({width:{size:CW,type:WidthType.DXA},columnWidths:[3120,3120,3120],rows:[
      new TableRow({children:PROOF.metrics.slice(0,3).map((m,i)=>metricCell(m,cols[i]))})]}),
    spacer(160),
    h2("The receipts"),
    ...(has("result-sendr.jpeg")?[
      body([b("1. Real Google Search Console — last 6 months. "),t("From a standing start, climbing the whole way.")],{after:40}),
      imgPara("result-sendr.jpeg",624,{after:40}),
      body([t(PROOF.gsc_caption,{italics:true,color:MUTE,size:18})],{align:AlignmentType.CENTER,after:200}),
    ]:[]),
    ...(has("result-ranked.jpeg")?[
      body([b("2. Ranked #2 in Google\u2019s AI Overview — above ZoomInfo. "),t(`For the category-defining query `),t(`\u201C${PROOF.query}\u201D`,{italics:true}),t(`, ${PROOF.client} is the cited source. That\u2019s the difference between renting traffic and owning the answer.`)],{after:40}),
      imgPara("result-ranked.jpeg",470,{after:40}),
      body([t(PROOF.ranked_caption,{italics:true,color:MUTE,size:18})],{align:AlignmentType.CENTER,after:160}),
    ]:[]),
    callout("In the founder\u2019s words",
      [t(`\u201C${PROOF.quote}\u201D`,{italics:true,size:22}),new TextRun({break:1}),t("  — "+PROOF.quote_attrib,{color:MUTE,size:19})],
      {fill:PAPER,accent:RED,labelColor:RED_DK}),
    new Paragraph({pageBreakBefore:true,children:[]}),
    h2("How we out-content the giants"),
    body([t(`${PROOF.client} is a startup competing against the category leaders. No matching budget, no matching team. The moat is a stack that lets one senior strategist out-publish a whole content department — speed to market is the whole game:`)],{after:120}),
    ...PROOF.engine.map(e=>bullet([b(e.b),t(e.t)])),
    callout("The result",PROOF.engine_result,{fill:PERITINT,accent:PERI}),
    spacer(120),
    callout(`What this means for ${CL}`,
      [t("The audit you just read is step one of this exact process. Same diagnosis, same stack, same obsession with being the cited answer — pointed at "),b(CL+"\u2019s"),t(" biggest opportunities. You already have authority most of our clients have to build from scratch. That\u2019s a head start.")],
      {fill:GREENTINT,accent:GREEN,labelColor:GREEN_DK}),
  ];
}

/* ============ NEXT ============ */
const next=[
  new Paragraph({pageBreakBefore:true,children:[]}),
  eyebrow("What happens next"),
  h1("Let\u2019s turn this into rankings"),
  body("Here\u2019s how I\u2019d suggest we play it:",{after:120}),
  ...(DATA.next||[
    {label:"This week:",text:"knock out the five quick wins above. Low-risk, high-return, fast movement."},
    {label:"Together:",text:"I\u2019ll walk your team through any finding, scope the dev items, and write the schema and meta copy so it\u2019s plug-and-play."},
    {label:"Then:",text:"we re-test once the first round is live, and decide whether to point the full engine at your biggest opportunities."},
  ]).map(n=>bullet([b(n.label+" "),t(n.text)])),
  spacer(120),
  body(DATA.nextOutro||"I take on four SaaS companies a month so each one gets senior attention, not a junior and a checklist. If it\u2019s a fit, I\u2019d love yours to be one of them."),
  spacer(120),
  new Table({width:{size:CW,type:WidthType.DXA},columnWidths:[CW],rows:[
    new TableRow({children:[new TableCell({width:{size:CW,type:WidthType.DXA},shading:{fill:PAPER,type:ShadingType.CLEAR},
      margins:{top:220,bottom:220,left:280,right:280},
      borders:{top:{style:BorderStyle.NONE},bottom:{style:BorderStyle.NONE},right:{style:BorderStyle.NONE},left:{style:BorderStyle.SINGLE,size:28,color:RED}},
      children:[
        new Paragraph({spacing:{after:40},children:[new TextRun({text:DATA.consultantName||"RankedTag",bold:true,color:INK,size:26,font:FONT})]}),
        new Paragraph({spacing:{after:80},children:[new TextRun({text:"SEO & Technical Audit · RankedTag",color:MUTE,size:20,font:FONT})]}),
        new Paragraph({children:[
          new TextRun({text:DATA.consultantEmail||"hello@rankedtag.com",color:PERI,size:20,font:FONT}),
          new TextRun({text:"      ·      ",color:MUTE,size:20,font:FONT}),
          new ExternalHyperlink({link:"https://rankedtag.com",children:[new TextRun({text:"rankedtag.com",color:PERI,size:20,font:FONT,underline:{}})]}),
        ]}),
      ]})]})]}),
];

/* ============ DOC ============ */
const doc=new Document({
  creator:"RankedTag", title:`SEO & AI-Search Audit — ${DATA.client}`,
  styles:{
    default:{document:{run:{font:FONT,size:21,color:INK}}},
    paragraphStyles:[
      {id:"Heading1",name:"Heading 1",basedOn:"Normal",next:"Normal",quickFormat:true,
       run:{size:30,bold:true,font:FONT,color:INK},paragraph:{spacing:{before:340,after:140},outlineLevel:0}},
      {id:"Heading2",name:"Heading 2",basedOn:"Normal",next:"Normal",quickFormat:true,
       run:{size:24,bold:true,font:FONT,color:INK},paragraph:{spacing:{before:240,after:90},outlineLevel:1}},
    ]},
  numbering:{config:[{reference:"bullets",levels:[{level:0,format:LevelFormat.BULLET,text:"\u2022",alignment:AlignmentType.LEFT,
    style:{run:{color:RED},paragraph:{indent:{left:460,hanging:260}}}}]}]},
  sections:[{
    properties:{page:{size:{width:12240,height:15840},margin:{top:1440,right:1440,bottom:1440,left:1440}}},
    footers:{default:new Footer({children:[new Paragraph({tabStops:[{type:"right",position:9360}],
      border:{top:{style:BorderStyle.SINGLE,size:4,color:LINE,space:6}},
      children:[
        new TextRun({text:`RankedTag  ·  SEO & AI-search audit for ${DATA.client}`,color:MUTE,size:16,font:FONT}),
        new TextRun({text:"\t",font:FONT}),
        new TextRun({children:[PageNumber.CURRENT],color:MUTE,size:16,font:FONT}),
      ]})]})},
    children:[...cover,...note,...why,...method,...critical,...high,...medium,...quick,...plan,...comp,...proof,...next],
  }]
});

Packer.toBuffer(doc).then(buf=>{fs.writeFileSync(OUT,buf);console.log("WROTE",OUT,buf.length,"bytes");});
