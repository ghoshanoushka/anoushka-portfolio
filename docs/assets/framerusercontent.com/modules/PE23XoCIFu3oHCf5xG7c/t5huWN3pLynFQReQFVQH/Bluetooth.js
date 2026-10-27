let r;
var f = (o) => {
    if (!r) {
        let e = function(t, n) {
            return o.createElement("svg", {width: "100%", height: "1.5em", strokeWidth: 1.5, viewBox: "0 0 24 24", fill: "none", xmlns: "http://www.w3.org/2000/svg", color: "currentColor", ref: n, ...t}, o.createElement("path", {d: "M6.75 8l10.5 8.5-5.5 5.5V2l5.5 5.5L6.75 16", stroke: "currentColor", strokeLinecap: "round", strokeLinejoin: "round"}));
        };
        r = o.forwardRef(e);
    }
    return r;
};
const __FramerMetadata__ = {exports: {default: {type: "reactComponent", slots: [], annotations: {framerContractVersion: "1"}}, __FramerMetadata__: {type: "variable"}}};
export { __FramerMetadata__, f as default };