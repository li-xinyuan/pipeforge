import{f as Ie,g as h,aQ as Bt,b4 as It,ai as qe,b5 as zt,b6 as Tt,aF as $t,n as ue,l as f,ac as de,u as et,s as Se,ae as tt,e as $,y as pe,w as Ge,af as Mt,x as O,aJ as Je,aK as at,b7 as it,J as X,a2 as Me,d as Re,b8 as Dt,K as nt,m as I,G as y,D as lt,aa as Ft,ab as Nt,b9 as At,T as Pt,a as Ot,v as Qe,aY as Ut,b as ze,a9 as rt,E as st,ba as Ee,ad as Ht,ao as Et,L as we,am as je,bb as se,a5 as jt,a0 as Lt,S as Te,R as x,O as E,W as ae,N as Le,V as _e,_ as Ke,Z as dt,at as Kt,$ as Wt,c as Yt,a6 as Xt,Q as $e,Y as We}from"./index-BGz2kfV9.js";import{i as Gt,u as ot,A as Jt,B as Qt,V as Zt,a as qt,k as Ze,g as en}from"./useWizardApi-nt71vZdf.js";import{i as tn,N as De,a as nn}from"./Select-BJHmCGQK.js";import{_ as on}from"./_plugin-vue_export-helper-DlAUqK2U.js";const an=Ie({name:"Remove",render(){return h("svg",{xmlns:"http://www.w3.org/2000/svg",viewBox:"0 0 512 512"},h("line",{x1:"400",y1:"256",x2:"112",y2:"256",style:`
        fill: none;
        stroke: currentColor;
        stroke-linecap: round;
        stroke-linejoin: round;
        stroke-width: 32px;
      `}))}});function ln(e){const{textColorDisabled:l}=e;return{iconColorDisabled:l}}const rn=Bt({name:"InputNumber",common:qe,peers:{Button:It,Input:tn},self:ln});function sn(e){const l="rgba(0, 0, 0, .85)",k="0 2px 8px 0 rgba(0, 0, 0, 0.12)",{railColor:p,primaryColor:u,baseColor:b,cardColor:N,modalColor:s,popoverColor:j,borderRadius:U,fontSize:M,opacityDisabled:R}=e;return Object.assign(Object.assign({},zt),{fontSize:M,markFontSize:M,railColor:p,railColorHover:p,fillColor:u,fillColorHover:u,opacityDisabled:R,handleColor:"#FFF",dotColor:N,dotColorModal:s,dotColorPopover:j,handleBoxShadow:"0 1px 4px 0 rgba(0, 0, 0, 0.3), inset 0 0 1px 0 rgba(0, 0, 0, 0.05)",handleBoxShadowHover:"0 1px 4px 0 rgba(0, 0, 0, 0.3), inset 0 0 1px 0 rgba(0, 0, 0, 0.05)",handleBoxShadowActive:"0 1px 4px 0 rgba(0, 0, 0, 0.3), inset 0 0 1px 0 rgba(0, 0, 0, 0.05)",handleBoxShadowFocus:"0 1px 4px 0 rgba(0, 0, 0, 0.3), inset 0 0 1px 0 rgba(0, 0, 0, 0.05)",indicatorColor:l,indicatorBoxShadow:k,indicatorTextColor:b,indicatorBorderRadius:U,dotBorder:`2px solid ${p}`,dotBorderActive:`2px solid ${u}`,dotBoxShadow:""})}const dn={common:qe,self:sn};function un(e){const{primaryColor:l,opacityDisabled:k,borderRadius:p,textColor3:u}=e;return Object.assign(Object.assign({},Tt),{iconColor:u,textColor:"white",loadingColor:l,opacityDisabled:k,railColor:"rgba(0, 0, 0, .14)",railColorActive:l,buttonBoxShadow:"0 1px 4px 0 rgba(0, 0, 0, 0.3), inset 0 0 1px 0 rgba(0, 0, 0, 0.05)",buttonColor:"#FFF",railBorderRadiusSmall:p,railBorderRadiusMedium:p,railBorderRadiusLarge:p,buttonBorderRadiusSmall:p,buttonBorderRadiusMedium:p,buttonBorderRadiusLarge:p,boxShadowFocus:`0 0 0 2px ${$t(l,{alpha:.2})}`})}const cn={common:qe,self:un},fn=ue([f("input-number-suffix",`
 display: inline-block;
 margin-right: 10px;
 `),f("input-number-prefix",`
 display: inline-block;
 margin-left: 10px;
 `)]);function hn(e){return e==null||typeof e=="string"&&e.trim()===""?null:Number(e)}function vn(e){return e.includes(".")&&(/^(-)?\d+.*(\.|0)$/.test(e)||/^-?\d*$/.test(e))||e==="-"||e==="-0"}function Ye(e){return e==null?!0:!Number.isNaN(e)}function ut(e,l){return typeof e!="number"?"":l===void 0?String(e):e.toFixed(l)}function Xe(e){if(e===null)return null;if(typeof e=="number")return e;{const l=Number(e);return Number.isNaN(l)?null:l}}const ct=800,ft=100,mn=Object.assign(Object.assign({},Se.props),{autofocus:Boolean,loading:{type:Boolean,default:void 0},placeholder:String,defaultValue:{type:Number,default:null},value:Number,step:{type:[Number,String],default:1},min:[Number,String],max:[Number,String],size:String,disabled:{type:Boolean,default:void 0},validator:Function,bordered:{type:Boolean,default:void 0},showButton:{type:Boolean,default:!0},buttonPlacement:{type:String,default:"right"},inputProps:Object,readonly:Boolean,clearable:Boolean,keyboard:{type:Object,default:{}},updateValueOnInput:{type:Boolean,default:!0},round:{type:Boolean,default:void 0},parse:Function,format:Function,precision:Number,status:String,"onUpdate:value":[Function,Array],onUpdateValue:[Function,Array],onFocus:[Function,Array],onBlur:[Function,Array],onClear:[Function,Array],onChange:[Function,Array]}),bn=Ie({name:"InputNumber",props:mn,slots:Object,setup(e){const{mergedBorderedRef:l,mergedClsPrefixRef:k,mergedRtlRef:p,mergedComponentPropsRef:u}=et(e),b=Se("InputNumber","-input-number",fn,rn,e,k),{localeRef:N}=Gt("InputNumber"),s=tt(e,{mergedSize:o=>{var r,c;const{size:_}=e;if(_)return _;const{mergedSize:B}=o||{};if(B!=null&&B.value)return B.value;const t=(c=(r=u==null?void 0:u.value)===null||r===void 0?void 0:r.InputNumber)===null||c===void 0?void 0:c.size;return t||"medium"}}),{mergedSizeRef:j,mergedDisabledRef:U,mergedStatusRef:M}=s,R=$(null),g=$(null),V=$(null),A=$(e.defaultValue),q=nt(e,"value"),D=ot(q,A),v=$(""),i=o=>{const r=String(o).split(".")[1];return r?r.length:0},ee=o=>{const r=[e.min,e.max,e.step,o].map(c=>c===void 0?0:i(c));return Math.max(...r)},S=pe(()=>{const{placeholder:o}=e;return o!==void 0?o:N.value.placeholder}),F=pe(()=>{const o=Xe(e.step);return o!==null?o===0?1:Math.abs(o):1}),me=pe(()=>{const o=Xe(e.min);return o!==null?o:null}),L=pe(()=>{const o=Xe(e.max);return o!==null?o:null}),z=()=>{const{value:o}=D;if(Ye(o)){const{format:r,precision:c}=e;r?v.value=r(o):o===null||c===void 0||i(o)>c?v.value=ut(o,void 0):v.value=ut(o,c)}else v.value=String(o)};z();const m=o=>{const{value:r}=D;if(o===r){z();return}const{"onUpdate:value":c,onUpdateValue:_,onChange:B}=e,{nTriggerFormInput:t,nTriggerFormChange:n}=s;B&&X(B,o),_&&X(_,o),c&&X(c,o),A.value=o,t(),n()},C=({offset:o,doUpdateIfValid:r,fixPrecision:c,isInputing:_})=>{const{value:B}=v;if(_&&vn(B))return!1;const t=(e.parse||hn)(B);if(t===null)return r&&m(null),null;if(Ye(t)){const n=i(t),{precision:a}=e;if(a!==void 0&&a<n&&!c)return!1;let d=Number.parseFloat((t+o).toFixed(a??ee(t)));if(Ye(d)){const{value:w}=L,{value:T}=me;if(w!==null&&d>w){if(!r||_)return!1;d=w}if(T!==null&&d<T){if(!r||_)return!1;d=T}return e.validator&&!e.validator(d)?!1:(r&&m(d),d)}}return!1},G=pe(()=>C({offset:0,doUpdateIfValid:!1,isInputing:!1,fixPrecision:!1})===!1),K=pe(()=>{const{value:o}=D;if(e.validator&&o===null)return!1;const{value:r}=F;return C({offset:-r,doUpdateIfValid:!1,isInputing:!1,fixPrecision:!1})!==!1}),ie=pe(()=>{const{value:o}=D;if(e.validator&&o===null)return!1;const{value:r}=F;return C({offset:+r,doUpdateIfValid:!1,isInputing:!1,fixPrecision:!1})!==!1});function ce(o){const{onFocus:r}=e,{nTriggerFormFocus:c}=s;r&&X(r,o),c()}function Ce(o){var r,c;if(o.target===((r=R.value)===null||r===void 0?void 0:r.wrapperElRef))return;const _=C({offset:0,doUpdateIfValid:!0,isInputing:!1,fixPrecision:!0});if(_!==!1){const n=(c=R.value)===null||c===void 0?void 0:c.inputElRef;n&&(n.value=String(_||"")),D.value===_&&z()}else z();const{onBlur:B}=e,{nTriggerFormBlur:t}=s;B&&X(B,o),t(),Me(()=>{z()})}function Ve(o){const{onClear:r}=e;r&&X(r,o)}function be(){const{value:o}=ie;if(!o){Q();return}const{value:r}=D;if(r===null)e.validator||m(he());else{const{value:c}=F;C({offset:c,doUpdateIfValid:!0,isInputing:!1,fixPrecision:!0})}}function fe(){const{value:o}=K;if(!o){te();return}const{value:r}=D;if(r===null)e.validator||m(he());else{const{value:c}=F;C({offset:-c,doUpdateIfValid:!0,isInputing:!1,fixPrecision:!0})}}const W=ce,ge=Ce;function he(){if(e.validator)return null;const{value:o}=me,{value:r}=L;return o!==null?Math.max(0,o):r!==null?Math.min(0,r):0}function Y(o){Ve(o),m(null)}function J(o){var r,c,_;!((r=V.value)===null||r===void 0)&&r.$el.contains(o.target)&&o.preventDefault(),!((c=g.value)===null||c===void 0)&&c.$el.contains(o.target)&&o.preventDefault(),(_=R.value)===null||_===void 0||_.activate()}let le=null,re=null,Z=null;function te(){Z&&(window.clearTimeout(Z),Z=null),le&&(window.clearInterval(le),le=null)}let ne=null;function Q(){ne&&(window.clearTimeout(ne),ne=null),re&&(window.clearInterval(re),re=null)}function Fe(){te(),Z=window.setTimeout(()=>{le=window.setInterval(()=>{fe()},ft)},ct),Re("mouseup",document,te,{once:!0})}function Ne(){Q(),ne=window.setTimeout(()=>{re=window.setInterval(()=>{be()},ft)},ct),Re("mouseup",document,Q,{once:!0})}const xe=()=>{re||be()},ye=()=>{le||fe()};function ke(o){var r,c;if(o.key==="Enter"){if(o.target===((r=R.value)===null||r===void 0?void 0:r.wrapperElRef))return;C({offset:0,doUpdateIfValid:!0,isInputing:!1,fixPrecision:!0})!==!1&&((c=R.value)===null||c===void 0||c.deactivate())}else if(o.key==="ArrowUp"){if(!ie.value||e.keyboard.ArrowUp===!1)return;o.preventDefault(),C({offset:0,doUpdateIfValid:!0,isInputing:!1,fixPrecision:!0})!==!1&&be()}else if(o.key==="ArrowDown"){if(!K.value||e.keyboard.ArrowDown===!1)return;o.preventDefault(),C({offset:0,doUpdateIfValid:!0,isInputing:!1,fixPrecision:!0})!==!1&&fe()}}function Ae(o){v.value=o,e.updateValueOnInput&&!e.format&&!e.parse&&e.precision===void 0&&C({offset:0,doUpdateIfValid:!0,isInputing:!0,fixPrecision:!1})}Ge(D,()=>{z()});const Pe={focus:()=>{var o;return(o=R.value)===null||o===void 0?void 0:o.focus()},blur:()=>{var o;return(o=R.value)===null||o===void 0?void 0:o.blur()},select:()=>{var o;return(o=R.value)===null||o===void 0?void 0:o.select()}},Oe=Mt("InputNumber",p,k);return Object.assign(Object.assign({},Pe),{rtlEnabled:Oe,inputInstRef:R,minusButtonInstRef:g,addButtonInstRef:V,mergedClsPrefix:k,mergedBordered:l,uncontrolledValue:A,mergedValue:D,mergedPlaceholder:S,displayedValueInvalid:G,mergedSize:j,mergedDisabled:U,displayedValue:v,addable:ie,minusable:K,mergedStatus:M,handleFocus:W,handleBlur:ge,handleClear:Y,handleMouseDown:J,handleAddClick:xe,handleMinusClick:ye,handleAddMousedown:Ne,handleMinusMousedown:Fe,handleKeyDown:ke,handleUpdateDisplayedValue:Ae,mergedTheme:b,inputThemeOverrides:{paddingSmall:"0 8px 0 10px",paddingMedium:"0 8px 0 12px",paddingLarge:"0 8px 0 14px"},buttonThemeOverrides:O(()=>{const{self:{iconColorDisabled:o}}=b.value,[r,c,_,B]=Dt(o);return{textColorTextDisabled:`rgb(${r}, ${c}, ${_})`,opacityDisabled:`${B}`}})})},render(){const{mergedClsPrefix:e,$slots:l}=this,k=()=>h(it,{text:!0,disabled:!this.minusable||this.mergedDisabled||this.readonly,focusable:!1,theme:this.mergedTheme.peers.Button,themeOverrides:this.mergedTheme.peerOverrides.Button,builtinThemeOverrides:this.buttonThemeOverrides,onClick:this.handleMinusClick,onMousedown:this.handleMinusMousedown,ref:"minusButtonInstRef"},{icon:()=>Je(l["minus-icon"],()=>[h(at,{clsPrefix:e},{default:()=>h(an,null)})])}),p=()=>h(it,{text:!0,disabled:!this.addable||this.mergedDisabled||this.readonly,focusable:!1,theme:this.mergedTheme.peers.Button,themeOverrides:this.mergedTheme.peerOverrides.Button,builtinThemeOverrides:this.buttonThemeOverrides,onClick:this.handleAddClick,onMousedown:this.handleAddMousedown,ref:"addButtonInstRef"},{icon:()=>Je(l["add-icon"],()=>[h(at,{clsPrefix:e},{default:()=>h(Jt,null)})])});return h("div",{class:[`${e}-input-number`,this.rtlEnabled&&`${e}-input-number--rtl`]},h(De,{ref:"inputInstRef",autofocus:this.autofocus,status:this.mergedStatus,bordered:this.mergedBordered,loading:this.loading,value:this.displayedValue,onUpdateValue:this.handleUpdateDisplayedValue,theme:this.mergedTheme.peers.Input,themeOverrides:this.mergedTheme.peerOverrides.Input,builtinThemeOverrides:this.inputThemeOverrides,size:this.mergedSize,placeholder:this.mergedPlaceholder,disabled:this.mergedDisabled,readonly:this.readonly,round:this.round,textDecoration:this.displayedValueInvalid?"line-through":void 0,onFocus:this.handleFocus,onBlur:this.handleBlur,onKeydown:this.handleKeyDown,onMousedown:this.handleMouseDown,onClear:this.handleClear,clearable:this.clearable,inputProps:this.inputProps,internalLoadingBeforeSuffix:!0},{prefix:()=>{var u;return this.showButton&&this.buttonPlacement==="both"?[k(),de(l.prefix,b=>b?h("span",{class:`${e}-input-number-prefix`},b):null)]:(u=l.prefix)===null||u===void 0?void 0:u.call(l)},suffix:()=>{var u;return this.showButton?[de(l.suffix,b=>b?h("span",{class:`${e}-input-number-suffix`},b):null),this.buttonPlacement==="right"?k():null,p()]:(u=l.suffix)===null||u===void 0?void 0:u.call(l)}}))}}),gn=ue([f("slider",`
 display: block;
 padding: calc((var(--n-handle-size) - var(--n-rail-height)) / 2) 0;
 position: relative;
 z-index: 0;
 width: 100%;
 cursor: pointer;
 user-select: none;
 -webkit-user-select: none;
 `,[I("reverse",[f("slider-handles",[f("slider-handle-wrapper",`
 transform: translate(50%, -50%);
 `)]),f("slider-dots",[f("slider-dot",`
 transform: translateX(50%, -50%);
 `)]),I("vertical",[f("slider-handles",[f("slider-handle-wrapper",`
 transform: translate(-50%, -50%);
 `)]),f("slider-marks",[f("slider-mark",`
 transform: translateY(calc(-50% + var(--n-dot-height) / 2));
 `)]),f("slider-dots",[f("slider-dot",`
 transform: translateX(-50%) translateY(0);
 `)])])]),I("vertical",`
 box-sizing: content-box;
 padding: 0 calc((var(--n-handle-size) - var(--n-rail-height)) / 2);
 width: var(--n-rail-width-vertical);
 height: 100%;
 `,[f("slider-handles",`
 top: calc(var(--n-handle-size) / 2);
 right: 0;
 bottom: calc(var(--n-handle-size) / 2);
 left: 0;
 `,[f("slider-handle-wrapper",`
 top: unset;
 left: 50%;
 transform: translate(-50%, 50%);
 `)]),f("slider-rail",`
 height: 100%;
 `,[y("fill",`
 top: unset;
 right: 0;
 bottom: unset;
 left: 0;
 `)]),I("with-mark",`
 width: var(--n-rail-width-vertical);
 margin: 0 32px 0 8px;
 `),f("slider-marks",`
 top: calc(var(--n-handle-size) / 2);
 right: unset;
 bottom: calc(var(--n-handle-size) / 2);
 left: 22px;
 font-size: var(--n-mark-font-size);
 `,[f("slider-mark",`
 transform: translateY(50%);
 white-space: nowrap;
 `)]),f("slider-dots",`
 top: calc(var(--n-handle-size) / 2);
 right: unset;
 bottom: calc(var(--n-handle-size) / 2);
 left: 50%;
 `,[f("slider-dot",`
 transform: translateX(-50%) translateY(50%);
 `)])]),I("disabled",`
 cursor: not-allowed;
 opacity: var(--n-opacity-disabled);
 `,[f("slider-handle",`
 cursor: not-allowed;
 `)]),I("with-mark",`
 width: 100%;
 margin: 8px 0 32px 0;
 `),ue("&:hover",[f("slider-rail",{backgroundColor:"var(--n-rail-color-hover)"},[y("fill",{backgroundColor:"var(--n-fill-color-hover)"})]),f("slider-handle",{boxShadow:"var(--n-handle-box-shadow-hover)"})]),I("active",[f("slider-rail",{backgroundColor:"var(--n-rail-color-hover)"},[y("fill",{backgroundColor:"var(--n-fill-color-hover)"})]),f("slider-handle",{boxShadow:"var(--n-handle-box-shadow-hover)"})]),f("slider-marks",`
 position: absolute;
 top: 18px;
 left: calc(var(--n-handle-size) / 2);
 right: calc(var(--n-handle-size) / 2);
 `,[f("slider-mark",`
 position: absolute;
 transform: translateX(-50%);
 white-space: nowrap;
 `)]),f("slider-rail",`
 width: 100%;
 position: relative;
 height: var(--n-rail-height);
 background-color: var(--n-rail-color);
 transition: background-color .3s var(--n-bezier);
 border-radius: calc(var(--n-rail-height) / 2);
 `,[y("fill",`
 position: absolute;
 top: 0;
 bottom: 0;
 border-radius: calc(var(--n-rail-height) / 2);
 transition: background-color .3s var(--n-bezier);
 background-color: var(--n-fill-color);
 `)]),f("slider-handles",`
 position: absolute;
 top: 0;
 right: calc(var(--n-handle-size) / 2);
 bottom: 0;
 left: calc(var(--n-handle-size) / 2);
 `,[f("slider-handle-wrapper",`
 outline: none;
 position: absolute;
 top: 50%;
 transform: translate(-50%, -50%);
 cursor: pointer;
 display: flex;
 `,[f("slider-handle",`
 height: var(--n-handle-size);
 width: var(--n-handle-size);
 border-radius: 50%;
 overflow: hidden;
 transition: box-shadow .2s var(--n-bezier), background-color .3s var(--n-bezier);
 background-color: var(--n-handle-color);
 box-shadow: var(--n-handle-box-shadow);
 `,[ue("&:hover",`
 box-shadow: var(--n-handle-box-shadow-hover);
 `)]),ue("&:focus",[f("slider-handle",`
 box-shadow: var(--n-handle-box-shadow-focus);
 `,[ue("&:hover",`
 box-shadow: var(--n-handle-box-shadow-active);
 `)])])])]),f("slider-dots",`
 position: absolute;
 top: 50%;
 left: calc(var(--n-handle-size) / 2);
 right: calc(var(--n-handle-size) / 2);
 `,[I("transition-disabled",[f("slider-dot","transition: none;")]),f("slider-dot",`
 transition:
 border-color .3s var(--n-bezier),
 box-shadow .3s var(--n-bezier),
 background-color .3s var(--n-bezier);
 position: absolute;
 transform: translate(-50%, -50%);
 height: var(--n-dot-height);
 width: var(--n-dot-width);
 border-radius: var(--n-dot-border-radius);
 overflow: hidden;
 box-sizing: border-box;
 border: var(--n-dot-border);
 background-color: var(--n-dot-color);
 `,[I("active","border: var(--n-dot-border-active);")])])]),f("slider-handle-indicator",`
 font-size: var(--n-font-size);
 padding: 6px 10px;
 border-radius: var(--n-indicator-border-radius);
 color: var(--n-indicator-text-color);
 background-color: var(--n-indicator-color);
 box-shadow: var(--n-indicator-box-shadow);
 `,[lt()]),f("slider-handle-indicator",`
 font-size: var(--n-font-size);
 padding: 6px 10px;
 border-radius: var(--n-indicator-border-radius);
 color: var(--n-indicator-text-color);
 background-color: var(--n-indicator-color);
 box-shadow: var(--n-indicator-box-shadow);
 `,[I("top",`
 margin-bottom: 12px;
 `),I("right",`
 margin-left: 12px;
 `),I("bottom",`
 margin-top: 12px;
 `),I("left",`
 margin-right: 12px;
 `),lt()]),Ft(f("slider",[f("slider-dot","background-color: var(--n-dot-color-modal);")])),Nt(f("slider",[f("slider-dot","background-color: var(--n-dot-color-popover);")]))]);function ht(e){return window.TouchEvent&&e instanceof window.TouchEvent}function vt(){const e=new Map,l=k=>p=>{e.set(k,p)};return At(()=>{e.clear()}),[e,l]}const pn=0,wn=Object.assign(Object.assign({},Se.props),{to:Ze.propTo,defaultValue:{type:[Number,Array],default:0},marks:Object,disabled:{type:Boolean,default:void 0},formatTooltip:Function,keyboard:{type:Boolean,default:!0},min:{type:Number,default:0},max:{type:Number,default:100},step:{type:[Number,String],default:1},range:Boolean,value:[Number,Array],placement:String,showTooltip:{type:Boolean,default:void 0},tooltip:{type:Boolean,default:!0},vertical:Boolean,reverse:Boolean,"onUpdate:value":[Function,Array],onUpdateValue:[Function,Array],onDragstart:[Function],onDragend:[Function]}),xn=Ie({name:"Slider",props:wn,slots:Object,setup(e){const{mergedClsPrefixRef:l,namespaceRef:k,inlineThemeDisabled:p}=et(e),u=Se("Slider","-slider",gn,dn,e,l),b=$(null),[N,s]=vt(),[j,U]=vt(),M=$(new Set),R=tt(e),{mergedDisabledRef:g}=R,V=O(()=>{const{step:t}=e;if(Number(t)<=0||t==="mark")return 0;const n=t.toString();let a=0;return n.includes(".")&&(a=n.length-n.indexOf(".")-1),a}),A=$(e.defaultValue),q=nt(e,"value"),D=ot(q,A),v=O(()=>{const{value:t}=D;return(e.range?t:[t]).map(Y)}),i=O(()=>v.value.length>2),ee=O(()=>e.placement===void 0?e.vertical?"right":"top":e.placement),S=O(()=>{const{marks:t}=e;return t?Object.keys(t).map(Number.parseFloat):null}),F=$(-1),me=$(-1),L=$(-1),z=$(!1),m=$(!1),C=O(()=>{const{vertical:t,reverse:n}=e;return t?n?"top":"bottom":n?"right":"left"}),G=O(()=>{if(i.value)return;const t=v.value,n=J(e.range?Math.min(...t):e.min),a=J(e.range?Math.max(...t):t[0]),{value:d}=C;return e.vertical?{[d]:`${n}%`,height:`${a-n}%`}:{[d]:`${n}%`,width:`${a-n}%`}}),K=O(()=>{const t=[],{marks:n}=e;if(n){const a=v.value.slice();a.sort((H,P)=>H-P);const{value:d}=C,{value:w}=i,{range:T}=e,oe=w?()=>!1:H=>T?H>=a[0]&&H<=a[a.length-1]:H<=a[0];for(const H of Object.keys(n)){const P=Number(H);t.push({active:oe(P),key:P,label:n[H],style:{[d]:`${J(P)}%`}})}}return t});function ie(t,n){const a=J(t),{value:d}=C;return{[d]:`${a}%`,zIndex:n===F.value?1:0}}function ce(t){return e.showTooltip||L.value===t||F.value===t&&z.value}function Ce(t){return z.value?!(F.value===t&&me.value===t):!0}function Ve(t){var n;~t&&(F.value=t,(n=N.get(t))===null||n===void 0||n.focus())}function be(){j.forEach((t,n)=>{ce(n)&&t.syncPosition()})}function fe(t){const{"onUpdate:value":n,onUpdateValue:a}=e,{nTriggerFormInput:d,nTriggerFormChange:w}=R;a&&X(a,t),n&&X(n,t),A.value=t,d(),w()}function W(t){const{range:n}=e;if(n){if(Array.isArray(t)){const{value:a}=v;t.join()!==a.join()&&fe(t)}}else Array.isArray(t)||v.value[0]!==t&&fe(t)}function ge(t,n){if(e.range){const a=v.value.slice();a.splice(n,1,t),W(a)}else W(t)}function he(t,n,a){const d=a!==void 0;a||(a=t-n>0?1:-1);const w=S.value||[],{step:T}=e;if(T==="mark"){const P=Z(t,w.concat(n),d?a:void 0);return P?P.value:n}if(T<=0)return n;const{value:oe}=V;let H;if(d){const P=Number((n/T).toFixed(oe)),ve=Math.floor(P),Ue=P>ve?ve:ve-1,He=P<ve?ve:ve+1;H=Z(n,[Number((Ue*T).toFixed(oe)),Number((He*T).toFixed(oe)),...w],a)}else{const P=re(t);H=Z(t,[...w,P])}return H?Y(H.value):n}function Y(t){return Math.min(e.max,Math.max(e.min,t))}function J(t){const{max:n,min:a}=e;return(t-a)/(n-a)*100}function le(t){const{max:n,min:a}=e;return a+(n-a)*t}function re(t){const{step:n,min:a}=e;if(Number(n)<=0||n==="mark")return t;const d=Math.round((t-a)/n)*n+a;return Number(d.toFixed(V.value))}function Z(t,n=S.value,a){if(!(n!=null&&n.length))return null;let d=null,w=-1;for(;++w<n.length;){const T=n[w]-t,oe=Math.abs(T);(a===void 0||T*a>0)&&(d===null||oe<d.distance)&&(d={index:w,distance:oe,value:n[w]})}return d}function te(t){const n=b.value;if(!n)return;const a=ht(t)?t.touches[0]:t,d=n.getBoundingClientRect();let w;return e.vertical?w=(d.bottom-a.clientY)/d.height:w=(a.clientX-d.left)/d.width,e.reverse&&(w=1-w),le(w)}function ne(t){if(g.value||!e.keyboard)return;const{vertical:n,reverse:a}=e;switch(t.key){case"ArrowUp":t.preventDefault(),Q(n&&a?-1:1);break;case"ArrowRight":t.preventDefault(),Q(!n&&a?-1:1);break;case"ArrowDown":t.preventDefault(),Q(n&&a?1:-1);break;case"ArrowLeft":t.preventDefault(),Q(!n&&a?1:-1);break}}function Q(t){const n=F.value;if(n===-1)return;const{step:a}=e,d=v.value[n],w=Number(a)<=0||a==="mark"?d:d+a*t;ge(he(w,d,t>0?1:-1),n)}function Fe(t){var n,a;if(g.value||!ht(t)&&t.button!==pn)return;const d=te(t);if(d===void 0)return;const w=v.value.slice(),T=e.range?(a=(n=Z(d,w))===null||n===void 0?void 0:n.index)!==null&&a!==void 0?a:-1:0;T!==-1&&(t.preventDefault(),Ve(T),Ne(),ge(he(d,v.value[T]),T))}function Ne(){z.value||(z.value=!0,e.onDragstart&&X(e.onDragstart),Re("touchend",document,ke),Re("mouseup",document,ke),Re("touchmove",document,ye),Re("mousemove",document,ye))}function xe(){z.value&&(z.value=!1,e.onDragend&&X(e.onDragend),ze("touchend",document,ke),ze("mouseup",document,ke),ze("touchmove",document,ye),ze("mousemove",document,ye))}function ye(t){const{value:n}=F;if(!z.value||n===-1){xe();return}const a=te(t);a!==void 0&&ge(he(a,v.value[n]),n)}function ke(){xe()}function Ae(t){F.value=t,g.value||(L.value=t)}function Pe(t){F.value===t&&(F.value=-1,xe()),L.value===t&&(L.value=-1)}function Oe(t){L.value=t}function o(t){L.value===t&&(L.value=-1)}Ge(F,(t,n)=>void Me(()=>me.value=n)),Ge(D,()=>{if(e.marks){if(m.value)return;m.value=!0,Me(()=>{m.value=!1})}Me(be)}),Ot(()=>{xe()});const r=O(()=>{const{self:{markFontSize:t,railColor:n,railColorHover:a,fillColor:d,fillColorHover:w,handleColor:T,opacityDisabled:oe,dotColor:H,dotColorModal:P,handleBoxShadow:ve,handleBoxShadowHover:Ue,handleBoxShadowActive:He,handleBoxShadowFocus:mt,dotBorder:bt,dotBoxShadow:gt,railHeight:pt,railWidthVertical:wt,handleSize:xt,dotHeight:yt,dotWidth:kt,dotBorderRadius:_t,fontSize:Rt,dotBorderActive:St,dotColorPopover:Ct},common:{cubicBezierEaseInOut:Vt}}=u.value;return{"--n-bezier":Vt,"--n-dot-border":bt,"--n-dot-border-active":St,"--n-dot-border-radius":_t,"--n-dot-box-shadow":gt,"--n-dot-color":H,"--n-dot-color-modal":P,"--n-dot-color-popover":Ct,"--n-dot-height":yt,"--n-dot-width":kt,"--n-fill-color":d,"--n-fill-color-hover":w,"--n-font-size":Rt,"--n-handle-box-shadow":ve,"--n-handle-box-shadow-active":He,"--n-handle-box-shadow-focus":mt,"--n-handle-box-shadow-hover":Ue,"--n-handle-color":T,"--n-handle-size":xt,"--n-opacity-disabled":oe,"--n-rail-color":n,"--n-rail-color-hover":a,"--n-rail-height":pt,"--n-rail-width-vertical":wt,"--n-mark-font-size":t}}),c=p?Qe("slider",void 0,r,e):void 0,_=O(()=>{const{self:{fontSize:t,indicatorColor:n,indicatorBoxShadow:a,indicatorTextColor:d,indicatorBorderRadius:w}}=u.value;return{"--n-font-size":t,"--n-indicator-border-radius":w,"--n-indicator-box-shadow":a,"--n-indicator-color":n,"--n-indicator-text-color":d}}),B=p?Qe("slider-indicator",void 0,_,e):void 0;return{mergedClsPrefix:l,namespace:k,uncontrolledValue:A,mergedValue:D,mergedDisabled:g,mergedPlacement:ee,isMounted:Ut(),adjustedTo:Ze(e),dotTransitionDisabled:m,markInfos:K,isShowTooltip:ce,shouldKeepTooltipTransition:Ce,handleRailRef:b,setHandleRefs:s,setFollowerRefs:U,fillStyle:G,getHandleStyle:ie,activeIndex:F,arrifiedValues:v,followerEnabledIndexSet:M,handleRailMouseDown:Fe,handleHandleFocus:Ae,handleHandleBlur:Pe,handleHandleMouseEnter:Oe,handleHandleMouseLeave:o,handleRailKeyDown:ne,indicatorCssVars:p?void 0:_,indicatorThemeClass:B==null?void 0:B.themeClass,indicatorOnRender:B==null?void 0:B.onRender,cssVars:p?void 0:r,themeClass:c==null?void 0:c.themeClass,onRender:c==null?void 0:c.onRender}},render(){var e;const{mergedClsPrefix:l,themeClass:k,formatTooltip:p}=this;return(e=this.onRender)===null||e===void 0||e.call(this),h("div",{class:[`${l}-slider`,k,{[`${l}-slider--disabled`]:this.mergedDisabled,[`${l}-slider--active`]:this.activeIndex!==-1,[`${l}-slider--with-mark`]:this.marks,[`${l}-slider--vertical`]:this.vertical,[`${l}-slider--reverse`]:this.reverse}],style:this.cssVars,onKeydown:this.handleRailKeyDown,onMousedown:this.handleRailMouseDown,onTouchstart:this.handleRailMouseDown},h("div",{class:`${l}-slider-rail`},h("div",{class:`${l}-slider-rail__fill`,style:this.fillStyle}),this.marks?h("div",{class:[`${l}-slider-dots`,this.dotTransitionDisabled&&`${l}-slider-dots--transition-disabled`]},this.markInfos.map(u=>h("div",{key:u.key,class:[`${l}-slider-dot`,{[`${l}-slider-dot--active`]:u.active}],style:u.style}))):null,h("div",{ref:"handleRailRef",class:`${l}-slider-handles`},this.arrifiedValues.map((u,b)=>{const N=this.isShowTooltip(b);return h(Qt,null,{default:()=>[h(Zt,null,{default:()=>h("div",{ref:this.setHandleRefs(b),class:`${l}-slider-handle-wrapper`,tabindex:this.mergedDisabled?-1:0,role:"slider","aria-valuenow":u,"aria-valuemin":this.min,"aria-valuemax":this.max,"aria-orientation":this.vertical?"vertical":"horizontal","aria-disabled":this.disabled,style:this.getHandleStyle(u,b),onFocus:()=>{this.handleHandleFocus(b)},onBlur:()=>{this.handleHandleBlur(b)},onMouseenter:()=>{this.handleHandleMouseEnter(b)},onMouseleave:()=>{this.handleHandleMouseLeave(b)}},Je(this.$slots.thumb,()=>[h("div",{class:`${l}-slider-handle`})]))}),this.tooltip&&h(qt,{ref:this.setFollowerRefs(b),show:N,to:this.adjustedTo,enabled:this.showTooltip&&!this.range||this.followerEnabledIndexSet.has(b),teleportDisabled:this.adjustedTo===Ze.tdkey,placement:this.mergedPlacement,containerClass:this.namespace},{default:()=>h(Pt,{name:"fade-in-scale-up-transition",appear:this.isMounted,css:this.shouldKeepTooltipTransition(b),onEnter:()=>{this.followerEnabledIndexSet.add(b)},onAfterLeave:()=>{this.followerEnabledIndexSet.delete(b)}},{default:()=>{var s;return N?((s=this.indicatorOnRender)===null||s===void 0||s.call(this),h("div",{class:[`${l}-slider-handle-indicator`,this.indicatorThemeClass,`${l}-slider-handle-indicator--${this.mergedPlacement}`],style:this.indicatorCssVars},typeof p=="function"?p(u):u)):null}})})]})})),this.marks?h("div",{class:`${l}-slider-marks`},this.markInfos.map(u=>h("div",{key:u.key,class:`${l}-slider-mark`,style:u.style},typeof u.label=="function"?u.label():u.label))):null))}}),yn=f("switch",`
 height: var(--n-height);
 min-width: var(--n-width);
 vertical-align: middle;
 user-select: none;
 -webkit-user-select: none;
 display: inline-flex;
 outline: none;
 justify-content: center;
 align-items: center;
`,[y("children-placeholder",`
 height: var(--n-rail-height);
 display: flex;
 flex-direction: column;
 overflow: hidden;
 pointer-events: none;
 visibility: hidden;
 `),y("rail-placeholder",`
 display: flex;
 flex-wrap: none;
 `),y("button-placeholder",`
 width: calc(1.75 * var(--n-rail-height));
 height: var(--n-rail-height);
 `),f("base-loading",`
 position: absolute;
 top: 50%;
 left: 50%;
 transform: translateX(-50%) translateY(-50%);
 font-size: calc(var(--n-button-width) - 4px);
 color: var(--n-loading-color);
 transition: color .3s var(--n-bezier);
 `,[rt({left:"50%",top:"50%",originalTransform:"translateX(-50%) translateY(-50%)"})]),y("checked, unchecked",`
 transition: color .3s var(--n-bezier);
 color: var(--n-text-color);
 box-sizing: border-box;
 position: absolute;
 white-space: nowrap;
 top: 0;
 bottom: 0;
 display: flex;
 align-items: center;
 line-height: 1;
 `),y("checked",`
 right: 0;
 padding-right: calc(1.25 * var(--n-rail-height) - var(--n-offset));
 `),y("unchecked",`
 left: 0;
 justify-content: flex-end;
 padding-left: calc(1.25 * var(--n-rail-height) - var(--n-offset));
 `),ue("&:focus",[y("rail",`
 box-shadow: var(--n-box-shadow-focus);
 `)]),I("round",[y("rail","border-radius: calc(var(--n-rail-height) / 2);",[y("button","border-radius: calc(var(--n-button-height) / 2);")])]),st("disabled",[st("icon",[I("rubber-band",[I("pressed",[y("rail",[y("button","max-width: var(--n-button-width-pressed);")])]),y("rail",[ue("&:active",[y("button","max-width: var(--n-button-width-pressed);")])]),I("active",[I("pressed",[y("rail",[y("button","left: calc(100% - var(--n-offset) - var(--n-button-width-pressed));")])]),y("rail",[ue("&:active",[y("button","left: calc(100% - var(--n-offset) - var(--n-button-width-pressed));")])])])])])]),I("active",[y("rail",[y("button","left: calc(100% - var(--n-button-width) - var(--n-offset))")])]),y("rail",`
 overflow: hidden;
 height: var(--n-rail-height);
 min-width: var(--n-rail-width);
 border-radius: var(--n-rail-border-radius);
 cursor: pointer;
 position: relative;
 transition:
 opacity .3s var(--n-bezier),
 background .3s var(--n-bezier),
 box-shadow .3s var(--n-bezier);
 background-color: var(--n-rail-color);
 `,[y("button-icon",`
 color: var(--n-icon-color);
 transition: color .3s var(--n-bezier);
 font-size: calc(var(--n-button-height) - 4px);
 position: absolute;
 left: 0;
 right: 0;
 top: 0;
 bottom: 0;
 display: flex;
 justify-content: center;
 align-items: center;
 line-height: 1;
 `,[rt()]),y("button",`
 align-items: center; 
 top: var(--n-offset);
 left: var(--n-offset);
 height: var(--n-button-height);
 width: var(--n-button-width-pressed);
 max-width: var(--n-button-width);
 border-radius: var(--n-button-border-radius);
 background-color: var(--n-button-color);
 box-shadow: var(--n-button-box-shadow);
 box-sizing: border-box;
 cursor: inherit;
 content: "";
 position: absolute;
 transition:
 background-color .3s var(--n-bezier),
 left .3s var(--n-bezier),
 opacity .3s var(--n-bezier),
 max-width .3s var(--n-bezier),
 box-shadow .3s var(--n-bezier);
 `)]),I("active",[y("rail","background-color: var(--n-rail-color-active);")]),I("loading",[y("rail",`
 cursor: wait;
 `)]),I("disabled",[y("rail",`
 cursor: not-allowed;
 opacity: .5;
 `)])]),kn=Object.assign(Object.assign({},Se.props),{size:String,value:{type:[String,Number,Boolean],default:void 0},loading:Boolean,defaultValue:{type:[String,Number,Boolean],default:!1},disabled:{type:Boolean,default:void 0},round:{type:Boolean,default:!0},"onUpdate:value":[Function,Array],onUpdateValue:[Function,Array],checkedValue:{type:[String,Number,Boolean],default:!0},uncheckedValue:{type:[String,Number,Boolean],default:!1},railStyle:Function,rubberBand:{type:Boolean,default:!0},spinProps:Object,onChange:[Function,Array]});let Be;const _n=Ie({name:"Switch",props:kn,slots:Object,setup(e){Be===void 0&&(typeof CSS<"u"?typeof CSS.supports<"u"?Be=CSS.supports("width","max(1px)"):Be=!1:Be=!0);const{mergedClsPrefixRef:l,inlineThemeDisabled:k,mergedComponentPropsRef:p}=et(e),u=Se("Switch","-switch",yn,cn,e,l),b=tt(e,{mergedSize(m){var C,G;if(e.size!==void 0)return e.size;if(m)return m.mergedSize.value;const K=(G=(C=p==null?void 0:p.value)===null||C===void 0?void 0:C.Switch)===null||G===void 0?void 0:G.size;return K||"medium"}}),{mergedSizeRef:N,mergedDisabledRef:s}=b,j=$(e.defaultValue),U=nt(e,"value"),M=ot(U,j),R=O(()=>M.value===e.checkedValue),g=$(!1),V=$(!1),A=O(()=>{const{railStyle:m}=e;if(m)return m({focused:V.value,checked:R.value})});function q(m){const{"onUpdate:value":C,onChange:G,onUpdateValue:K}=e,{nTriggerFormInput:ie,nTriggerFormChange:ce}=b;C&&X(C,m),K&&X(K,m),G&&X(G,m),j.value=m,ie(),ce()}function D(){const{nTriggerFormFocus:m}=b;m()}function v(){const{nTriggerFormBlur:m}=b;m()}function i(){e.loading||s.value||(M.value!==e.checkedValue?q(e.checkedValue):q(e.uncheckedValue))}function ee(){V.value=!0,D()}function S(){V.value=!1,v(),g.value=!1}function F(m){e.loading||s.value||m.key===" "&&(M.value!==e.checkedValue?q(e.checkedValue):q(e.uncheckedValue),g.value=!1)}function me(m){e.loading||s.value||m.key===" "&&(m.preventDefault(),g.value=!0)}const L=O(()=>{const{value:m}=N,{self:{opacityDisabled:C,railColor:G,railColorActive:K,buttonBoxShadow:ie,buttonColor:ce,boxShadowFocus:Ce,loadingColor:Ve,textColor:be,iconColor:fe,[we("buttonHeight",m)]:W,[we("buttonWidth",m)]:ge,[we("buttonWidthPressed",m)]:he,[we("railHeight",m)]:Y,[we("railWidth",m)]:J,[we("railBorderRadius",m)]:le,[we("buttonBorderRadius",m)]:re},common:{cubicBezierEaseInOut:Z}}=u.value;let te,ne,Q;return Be?(te=`calc((${Y} - ${W}) / 2)`,ne=`max(${Y}, ${W})`,Q=`max(${J}, calc(${J} + ${W} - ${Y}))`):(te=je((se(Y)-se(W))/2),ne=je(Math.max(se(Y),se(W))),Q=se(Y)>se(W)?J:je(se(J)+se(W)-se(Y))),{"--n-bezier":Z,"--n-button-border-radius":re,"--n-button-box-shadow":ie,"--n-button-color":ce,"--n-button-width":ge,"--n-button-width-pressed":he,"--n-button-height":W,"--n-height":ne,"--n-offset":te,"--n-opacity-disabled":C,"--n-rail-border-radius":le,"--n-rail-color":G,"--n-rail-color-active":K,"--n-rail-height":Y,"--n-rail-width":J,"--n-width":Q,"--n-box-shadow-focus":Ce,"--n-loading-color":Ve,"--n-text-color":be,"--n-icon-color":fe}}),z=k?Qe("switch",O(()=>N.value[0]),L,e):void 0;return{handleClick:i,handleBlur:S,handleFocus:ee,handleKeyup:F,handleKeydown:me,mergedRailStyle:A,pressed:g,mergedClsPrefix:l,mergedValue:M,checked:R,mergedDisabled:s,cssVars:k?void 0:L,themeClass:z==null?void 0:z.themeClass,onRender:z==null?void 0:z.onRender}},render(){const{mergedClsPrefix:e,mergedDisabled:l,checked:k,mergedRailStyle:p,onRender:u,$slots:b}=this;u==null||u();const{checked:N,unchecked:s,icon:j,"checked-icon":U,"unchecked-icon":M}=b,R=!(Ee(j)&&Ee(U)&&Ee(M));return h("div",{role:"switch","aria-checked":k,class:[`${e}-switch`,this.themeClass,R&&`${e}-switch--icon`,k&&`${e}-switch--active`,l&&`${e}-switch--disabled`,this.round&&`${e}-switch--round`,this.loading&&`${e}-switch--loading`,this.pressed&&`${e}-switch--pressed`,this.rubberBand&&`${e}-switch--rubber-band`],tabindex:this.mergedDisabled?void 0:0,style:this.cssVars,onClick:this.handleClick,onFocus:this.handleFocus,onBlur:this.handleBlur,onKeyup:this.handleKeyup,onKeydown:this.handleKeydown},h("div",{class:`${e}-switch__rail`,"aria-hidden":"true",style:p},de(N,g=>de(s,V=>g||V?h("div",{"aria-hidden":!0,class:`${e}-switch__children-placeholder`},h("div",{class:`${e}-switch__rail-placeholder`},h("div",{class:`${e}-switch__button-placeholder`}),g),h("div",{class:`${e}-switch__rail-placeholder`},h("div",{class:`${e}-switch__button-placeholder`}),V)):null)),h("div",{class:`${e}-switch__button`},de(j,g=>de(U,V=>de(M,A=>h(Ht,null,{default:()=>this.loading?h(Et,Object.assign({key:"loading",clsPrefix:e,strokeWidth:20},this.spinProps)):this.checked&&(V||g)?h("div",{class:`${e}-switch__button-icon`,key:V?"checked-icon":"icon"},V||g):!this.checked&&(A||g)?h("div",{class:`${e}-switch__button-icon`,key:A?"unchecked-icon":"icon"},A||g):null})))),de(N,g=>g&&h("div",{key:"checked",class:`${e}-switch__checked`},g)),de(s,g=>g&&h("div",{key:"unchecked",class:`${e}-switch__unchecked`},g)))))}}),Rn={class:"settings"},Sn={class:"settings__nav"},Cn={class:"settings__nav-inner"},Vn={class:"settings__nav-links"},Bn=["title"],In={class:"settings__body"},zn={class:"settings__card"},Tn={class:"settings__row"},$n={class:"settings__field"},Mn={class:"settings__field"},Dn={class:"settings__hint"},Fn={class:"settings__field"},Nn={key:0,class:"settings__hint"},An={class:"settings__field"},Pn={class:"settings__field"},On={class:"settings__field-label"},Un={class:"settings__field"},Hn={class:"settings__actions"},En={key:1,class:"settings__result settings__result--ok"},jn=Ie({__name:"SettingsPage",setup(e){const l=Wt(),{isDark:k,toggleTheme:p}=jt(),{getAiSettings:u,updateAiSettings:b,testAiConnection:N}=en(),s=Yt({provider:"openai",api_key:"",base_url:"",model:"",temperature:.7,max_tokens:4096,enabled:!1}),j=[{label:"OpenAI",value:"openai"},{label:"Anthropic",value:"anthropic"},{label:"Custom (OpenAI-compatible)",value:"custom"}],U=$(""),M=$(!1),R=$(!1),g=$(null),V=$(""),A=O(()=>s.provider==="anthropic"?"claude-sonnet-4-6":"gpt-4o");Lt(async()=>{const v=await u();v&&(s.provider=v.provider,s.base_url=v.base_url,s.model=v.model,s.temperature=v.temperature,s.max_tokens=v.max_tokens,s.enabled=v.enabled,U.value=v.api_key)});async function q(){M.value=!0,g.value=null;try{await D();const{ok:v,data:i}=await N();v&&i?g.value={ok:!0,msg:`连接成功！${i.provider}/${i.model}，延迟 ${i.latency_ms}ms`}:g.value={ok:!1,msg:(i==null?void 0:i.detail)||"连接失败"}}catch{g.value={ok:!1,msg:"网络请求失败"}}finally{M.value=!1}}async function D(){R.value=!0,V.value="";try{const v={...s};if(v.api_key||(v.api_key=null),await b(v)){V.value="设置已保存";const ee=await u();ee&&(U.value=ee.api_key),setTimeout(()=>V.value="",3e3)}}finally{R.value=!1}}return(v,i)=>{const ee=Xt("router-link");return $e(),Te("div",Rn,[x("header",Sn,[x("div",Cn,[x("div",{class:"settings__brand",onClick:i[0]||(i[0]=S=>E(l).push("/"))},[...i[9]||(i[9]=[x("span",{class:"settings__brand-icon"},"⚡",-1),x("span",{class:"settings__brand-text"},"ConfigForge",-1)])]),x("nav",Vn,[ae(ee,{to:"/",class:"settings__nav-link"},{default:Le(()=>[...i[10]||(i[10]=[We("首页",-1)])]),_:1}),i[11]||(i[11]=x("span",{class:"settings__nav-link settings__nav-link--active"},"AI 模型设置",-1))]),x("button",{class:"settings__theme-toggle",onClick:i[1]||(i[1]=(...S)=>E(p)&&E(p)(...S)),title:E(k)?"切换到亮色模式":"切换到暗色模式"},_e(E(k)?"☀":"☾"),9,Bn)])]),x("div",In,[i[22]||(i[22]=x("h1",{class:"settings__title"},"AI 模型配置",-1)),x("div",zn,[x("div",Tn,[i[12]||(i[12]=x("span",{class:"settings__label"},"启用 AI",-1)),ae(E(_n),{value:s.enabled,"onUpdate:value":i[2]||(i[2]=S=>s.enabled=S)},null,8,["value"])]),i[20]||(i[20]=x("div",{class:"settings__divider"},null,-1)),x("div",$n,[i[13]||(i[13]=x("label",{class:"settings__field-label"},"提供商",-1)),ae(E(nn),{value:s.provider,"onUpdate:value":i[3]||(i[3]=S=>s.provider=S),options:j},null,8,["value"])]),x("div",Mn,[i[14]||(i[14]=x("label",{class:"settings__field-label"},"模型",-1)),ae(E(De),{value:s.model,"onUpdate:value":i[4]||(i[4]=S=>s.model=S),placeholder:A.value},null,8,["value","placeholder"]),x("p",Dn,"留空使用默认："+_e(A.value),1)]),x("div",Fn,[i[15]||(i[15]=x("label",{class:"settings__field-label"},"API Key",-1)),ae(E(De),{value:s.api_key,"onUpdate:value":i[5]||(i[5]=S=>s.api_key=S),type:"password",placeholder:"sk-...","show-password-toggle":""},null,8,["value"]),U.value?($e(),Te("p",Nn,"当前："+_e(U.value),1)):Ke("",!0)]),x("div",An,[i[16]||(i[16]=x("label",{class:"settings__field-label"},"Base URL",-1)),ae(E(De),{value:s.base_url,"onUpdate:value":i[6]||(i[6]=S=>s.base_url=S),placeholder:s.provider==="openai"?"https://api.openai.com/v1（默认）":"必填"},null,8,["value","placeholder"])]),x("div",Pn,[x("label",On,"Temperature: "+_e(s.temperature),1),ae(E(xn),{value:s.temperature,"onUpdate:value":i[7]||(i[7]=S=>s.temperature=S),min:0,max:2,step:.1},null,8,["value"])]),x("div",Un,[i[17]||(i[17]=x("label",{class:"settings__field-label"},"Max Tokens",-1)),ae(E(bn),{value:s.max_tokens,"onUpdate:value":i[8]||(i[8]=S=>s.max_tokens=S),min:256,max:65536,class:"w-full"},null,8,["value"])]),i[21]||(i[21]=x("div",{class:"settings__divider"},null,-1)),x("div",Hn,[ae(E(dt),{loading:M.value,onClick:q},{default:Le(()=>[...i[18]||(i[18]=[We("测试连接",-1)])]),_:1},8,["loading"]),ae(E(dt),{type:"primary",class:"btn-primary",loading:R.value,onClick:D},{default:Le(()=>[...i[19]||(i[19]=[We("保存设置",-1)])]),_:1},8,["loading"])]),g.value?($e(),Te("p",{key:0,class:Kt(["settings__result",g.value.ok?"settings__result--ok":"settings__result--error"])},_e(g.value.msg),3)):Ke("",!0),V.value?($e(),Te("p",En,_e(V.value),1)):Ke("",!0)])])])}}}),Xn=on(jn,[["__scopeId","data-v-5fcbc6b6"]]);export{Xn as default};
