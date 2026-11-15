const site='https://sites.google.com/view/sahanasundar/';
const pages=[['Home','home'],['Profile','profile'],['Education','education'],['Honors, Certifications, & Awards','honors-certifications-awards'],['Internships','internships'],['Work Experience','work-experience'],['Sports','sports'],['High School Clubs','high-school-clubs'],['Music, Culture','music-culture'],['References, Certificates','references-certificates'],['Languages','languages'],['Media and Public Recognition','media-and-public-recognition'],['Other Milestones','other-milestones'],['Other Courses, Certifications','other-courses-certifications'],['Gallery','gallery']];
const link=([name,slug])=>{const a=document.createElement('a');a.textContent=name;a.href=site+slug;a.target='_blank';a.rel='noopener noreferrer';return a};
for(const p of pages){document.querySelector('#pages').append(link(p))}
for(const p of pages.slice(0,5)){document.querySelector('#nav').append(link(p))}
document.querySelector('#year').textContent=new Date().getFullYear();
document.querySelector('#menuButton').onclick=()=>{const nav=document.querySelector('#nav');const open=nav.classList.toggle('open');document.querySelector('#menuButton').setAttribute('aria-expanded',String(open))};
