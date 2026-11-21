// Pip the Chatbot Dog: a 3D-printable sitting dog whose chest holds the
// LCDWIKI ES3C35P 3.5" ESP32-S3 touchscreen board (the screen is the dog's chest).
//
// Every part prints flat without supports on a small FDM printer (~180 mm bed).
//   openscad -D 'part="body"' -o stl/body.stl pip_dog.scad       (or run ./build.sh)
// Parts: assembly, exploded, front_plate, body, head_top, head_bottom, ear_left,
//        ear_right, collar, base, tail
// Units: mm. Board numbers are from the vendor drawing (reference/ES3C35P_size.pdf).
// Axes: X = dog's left-right, Y = front(-)/back(+), Z = up.

part = "assembly";

/* [Board: ES3C35P] */
pcb_w = 54.5;  pcb_h = 101.5;  pcb_t = 1.6;
glass_t = 4.2;                 // touch glass + LCD + glue, in front of the PCB
hole_dx = 47.9; hole_dz = 94.5;                    // M3 mounting holes (Ø3.2)
glass_h = 83.0; glass_top = 9.25;                  // glass outline, from the PCB top edge
va_w = 49.96; va_h = 74.44; va_top = 10.90;        // visible screen area
mic_from_right = 9.82; mic_from_top = 3.94;        // mic, seen from the front

/* [Enclosure] */
wall = 2.4;            // 6 perimeters with a 0.4 mm nozzle
fit = 0.3;             // clearance between parts that slide together
plate_t = 2.4;         // front plate (chest) thickness
body_depth = 38;       // depth of the body at the shoulders, incl. the plate
usb_room = 14;         // free height under the board for a 90-degree USB-C plug
speaker_d = 28;        // round speaker diameter: MEASURE YOURS (0 = no pocket)

/* [Dog] */
head_w = 86; head_d = 68; head_h = 64;   // cranium
snout_len = 24; snout_w = 34;
ear_len = 50; ear_w = 28; ear_t = 3;
leg_d = 15; leg_h = 52;                  // front legs
base_t = 4;

$fn = 72;
eps = 0.01;

// ---------------------------------------------------------------- derived
body_w = pcb_w + 2 * (wall + fit) + 6;     // shoulder width (front view)
board_z0 = wall + usb_room;                // board bottom edge above the body floor
body_h = board_z0 + pcb_h + 7;             // open top; the collar's rim drops 4 mm into it
board_x0 = (body_w - pcb_w) / 2;
// body cross-sections, bottom to top: [z, x_left, x_right, depth, corner radius]
slabs = [[0, -9, body_w + 9, body_depth + 16, 14],
         [body_h * 0.42, -4, body_w + 4, body_depth + 8, 12],
         [body_h - 1, 1, body_w - 1, body_depth - 2, 9]];

// ---------------------------------------------------------------- helpers
module rounded_box(size, r) {          // rounded vertical edges, flat top and bottom
    r2 = min(r, size[0] / 2 - eps, size[1] / 2 - eps);
    hull() for (x = [r2, size[0] - r2], y = [r2, size[1] - r2])
        translate([x, y, 0]) cylinder(r = r2, h = size[2]);
}
module half_dome() { intersection() { sphere(1); translate([-1, -1, 0]) cube(2); } }

// Body shape, inset by i (0 = outside surface). The chest (y = 0 plane) stays flat.
module body_shape(i = 0, y_front = 0) {
    hull() for (s = slabs)
        translate([s[1] + i, y_front, min(max(s[0], i), body_h - 1 - i)])
            rounded_box([s[2] - s[1] - 2 * i, s[3] - i - y_front, 1], s[4] - i);
}
module hole_positions() {
    for (sx = [-1, 1], sz = [-1, 1])
        translate([board_x0 + pcb_w / 2 + sx * hole_dx / 2, 0,
                   board_z0 + pcb_h / 2 + sz * hole_dz / 2]) children();
}
function plate_screws() = [for (sx = [-1, 1]) [body_w / 2 + sx * 17, wall + 5]];  // bottom only;
                                                   // the collar's lip holds the plate's top edge
peg_y = (body_depth - 2) / 2;                      // neck pegs: collar <-> head
head_y = body_depth / 2 - 4;                       // head position (body frame)
window_z0 = board_z0 + pcb_h - va_top - va_h;
window_x0 = board_x0 + (pcb_w - va_w) / 2;

// ---------------------------------------------------------------- front plate (the chest)
// Drops into a recess at the front of the body. Prints face-down: no supports.
module front_plate() {
    difference() {
        union() {
            intersection() {
                translate([-20, 0, -1]) cube([body_w + 40, plate_t, body_h + 2]);
                body_shape(wall / 2 + fit, -1);
            }
            hole_positions() rotate([-90, 0, 0])            // standoffs to the PCB front
                translate([0, 0, plate_t - eps]) cylinder(d = 6.4, h = glass_t);
        }
        // screen window, bevelled on the outside for comfortable touch
        hull() {
            translate([window_x0 - 0.3, plate_t - 0.6, window_z0 - 0.3]) cube([va_w + 0.6, 1, va_h + 0.6]);
            translate([window_x0 - 2.0, -eps - 0.01, window_z0 - 2.0]) cube([va_w + 4.0, 0.02, va_h + 4.0]);
        }
        translate([window_x0 - 0.3, -1, window_z0 - 0.3]) cube([va_w + 0.6, plate_t + 2, va_h + 0.6]);
        // pocket for the glass so the board sits flush against the standoffs
        translate([board_x0 - fit, plate_t - 0.6, board_z0 + pcb_h - glass_top - glass_h - fit])
            cube([pcb_w + 2 * fit, 1, glass_h + 2 * fit]);
        hole_positions() rotate([-90, 0, 0]) translate([0, 0, 0.8]) cylinder(d = 2.6, h = 20); // M3 pilot
        translate([board_x0 + pcb_w - mic_from_right, -1, board_z0 + pcb_h - mic_from_top])
            rotate([-90, 0, 0]) cylinder(d = 2.2, h = plate_t + 2);                           // mic
        for (p = plate_screws()) translate([p[0], -eps, p[1]]) rotate([-90, 0, 0]) {          // countersunk
            cylinder(d = 3.4, h = plate_t + 1);
            cylinder(d1 = 6.6, d2 = 3.4, h = 1.6);
        }
    }
}

// ---------------------------------------------------------------- body shell
// Prints lying on its back (the open chest faces up): no supports.
module body() {
    difference() {
        union() {
            difference() {
                body_shape(0, 0);
                hull() { body_shape(wall, -1); translate([0, 0, 20]) body_shape(wall, -1); } // hollow: open chest + top
                intersection() {                                       // recess for the plate
                    translate([-30, -1, -1]) cube([body_w + 60, plate_t + 1, body_h + 2]);
                    body_shape(wall / 2, -1);
                }
            }
            for (p = plate_screws()) translate([p[0] - 4, plate_t, 0])
                cube([8, 10, p[1] + 3.75]);                            // plate screw pillars (from the floor)
            for (sx = [-1, 1]) translate([body_w / 2 + sx * 14, body_depth * 0.45, wall - eps])
                cylinder(d = 7.5, h = 6);                              // base screw bosses
            if (speaker_d > 0)                                         // speaker ring
                translate([body_w / 2, body_depth + 4 - wall, body_h * 0.5]) rotate([90, 0, 0])
                    difference() { cylinder(d = speaker_d + 5, h = 3); translate([0, 0, -1]) cylinder(d = speaker_d + 0.6, h = 5); }
        }
        for (p = plate_screws()) translate([p[0], plate_t - 1, p[1]]) rotate([-90, 0, 0])
            cylinder(d = 2.6, h = 12);
        for (sx = [-1, 1]) translate([body_w / 2 + sx * 14, body_depth * 0.45, -1])
            cylinder(d = 2.6, h = wall + 8);
        // speaker grille in the dog's back
        if (speaker_d > 0)
            translate([body_w / 2, body_depth + 6 - wall - 1, body_h * 0.5]) rotate([-90, 0, 0])
                for (r = [0 : 4 : speaker_d / 2 - 3], a = [0 : (r == 0 ? 360 : 360 / floor(r * 1.6)) : 359])
                    rotate([0, 0, a]) translate([r, 0, -10]) cylinder(d = 2.4, h = 30, $fn = 16);
        // USB cable exit at the back of the floor
        translate([body_w / 2 - 6, body_depth * 0.5, -1]) cube([12, 40, 9]);
        // tail socket, neck pegs
        translate([body_w / 2, body_depth, 30]) rotate([-90, 0, 0]) translate([0, 0, -12]) cylinder(d = 6.4, h = 30);
    }
}

// ---------------------------------------------------------------- head (two halves) + collar
head_split_z = head_h * 0.34;
module head_solid() {
    hull() {   // cranium + cheeks
        translate([0, 0, head_h * 0.5]) scale([head_w / 2, head_d / 2, head_h / 2]) sphere(1);
        translate([0, -head_d * 0.12, head_h * 0.32]) scale([head_w * 0.45, head_d * 0.4, head_h * 0.3]) sphere(1);
        translate([0, 0, 0]) cylinder(d = 40, h = 1);
    }
    hull() {   // snout (forward = -Y)
        translate([0, -head_d * 0.3, head_h * 0.34]) scale([snout_w / 2, 12, 14]) sphere(1);
        translate([0, -head_d / 2 - snout_len * 0.5, head_h * 0.32]) scale([snout_w * 0.38, 10, 10.5]) sphere(1);
    }
    translate([0, -head_d / 2 - snout_len * 0.5 - 8, head_h * 0.39]) scale([7.5, 5.5, 6]) sphere(1);  // nose
}
ear_z = head_h * 0.68;
function ear_x() = head_w / 2 * sqrt(1 - pow((ear_z - head_h * 0.5) / (head_h / 2), 2));
module head() {
    difference() {
        head_solid();
        for (sx = [-1, 1]) {
            translate([sx * 16, -head_d * 0.45 + 2.5, head_h * 0.6]) rotate([90, 0, 0])
                cylinder(d = 10.5, h = 12);                                // eye sockets: 10 mm googly eyes
            translate([sx * (ear_x() + 1), 0, ear_z]) rotate([0, sx * 90, 0]) translate([0, 0, -10])
                cylinder(d = 5.6, h = 12);                                                                    // ear pegs
            translate([sx * 14, peg_y - head_y, -1]) cylinder(d = 6.4, h = 10);              // neck pegs
        }
        translate([0, -head_d / 2 - snout_len * 0.5, head_h * 0.27]) rotate([0, 90, 0])                     // smile
            translate([0, 0, -9]) rotate_extrude_arc();
        for (p = [[-20, 8], [20, 8], [0, -head_d * 0.38]])                                                   // alignment pins
            translate([p[0], p[1], head_split_z - 5]) cylinder(d = 3.3, h = 10);
    }
}
module rotate_extrude_arc() { linear_extrude(18) translate([0, 0]) difference() { circle(d = 12); circle(d = 10); translate([-10, 0]) square(20); } }
module head_top()    { intersection() { head(); translate([-150, -150, head_split_z]) cube(300); } }
module head_bottom() { intersection() { head(); translate([-150, -150, head_split_z - 300]) cube(300); } }
module collar() {      // lid of the body: rim drops into the open top, lip holds the chest plate
    top = slabs[2];        // body top outline: [z, x_left, x_right, depth, r]
    difference() {
        union() {
            translate([top[1] - 3, -3, 0]) rounded_box([top[2] - top[1] + 6, top[3] + 6, 6], top[4] + 3);
            translate([body_w / 2, -9, 0]) cylinder(d = 14, h = 6);                       // name tag
            intersection() {                                                               // rim (goes down)
                translate([0, 0, -4]) cube([body_w, body_depth, 4.01]);
                translate([0, 0, -body_h + 0.01]) body_shape(wall + fit, plate_t + fit);
            }
            translate([board_x0, -2.2, -3]) cube([pcb_w, 2.2, 3.01]);                      // front lip
        }
        for (sx = [-1, 1]) translate([body_w / 2 + sx * 14, peg_y, -5]) cylinder(d = 6.4, h = 12);
        translate([body_w / 2, -9, 4.8]) linear_extrude(2) text("PIP", size = 4.6, halign = "center",
            valign = "center", font = "Liberation Sans:style=Bold");                       // engraved name
    }
}

// ---------------------------------------------------------------- ears, tail, pegs
module ear() {   // floppy ear lying flat, with a peg that plugs into the side of the head
    hull() {
        cylinder(d = ear_w * 0.6, h = ear_t);
        translate([0, -(ear_len - ear_w / 2), 0]) scale([1, 1.15, 1]) cylinder(d = ear_w, h = ear_t);
    }
    translate([0, -4, ear_t - eps]) cylinder(d = 5.0, h = 8);
}
module tail() {  // curled tail lying flat, with a peg into the back
    linear_extrude(height = 7) for (a = [0 : 10 : 130]) hull() {
        rotate(a) translate([16, 0]) circle(d = 8 - a / 40);
        rotate(a + 10) translate([16, 0]) circle(d = 8 - (a + 10) / 40);
    }
    translate([16, 0, 3.5]) rotate([0, 90, 0]) translate([0, 0, -10]) cylinder(d = 5.8, h = 10.5);
}
module neck_peg() { cylinder(d = 5.9, h = 18); }   // print 2: joins body, collar and head

// ---------------------------------------------------------------- base: legs, paws, haunches
base_w = (slabs[0][2] - slabs[0][1]) + 30;
base_d = slabs[0][3] + 42;
module base() {
    difference() {
        union() {
            translate([0, base_d / 2 - 38, 0]) scale([base_w, base_d, 1]) cylinder(d = 1, h = base_t);
            for (sx = [-1, 1]) {
                hull() {   // front leg: a column standing in front of the chest, beside the screen
                    translate([sx * 33, -12, base_t]) cylinder(d = leg_d, h = leg_h - 4);
                    translate([sx * 33, -10, base_t + leg_h - 4]) sphere(d = leg_d);
                }
                translate([sx * 33, -19, base_t - eps]) scale([10, 13, 8]) half_dome();      // paw
                translate([sx * (slabs[0][2] - slabs[0][1]) / 2, slabs[0][3] * 0.55, base_t - eps])
                    scale([15, 26, 30]) half_dome();                                          // haunch
            }
        }
        for (sx = [-1, 1], t = [-3.5, 3.5])                                                     // toes
            translate([sx * 33 + t, -30.5, base_t + 2]) rotate([-35, 0, 0]) cube([1.4, 10, 6], center = true);
        for (sx = [-1, 1]) translate([sx * 14, body_depth * 0.45, -eps]) {                     // screws
            cylinder(d = 3.4, h = base_t + 1);
            cylinder(d1 = 6.6, d2 = 3.4, h = 1.6);
        }
    }
}

// ---------------------------------------------------------------- assembly views
module body_assembled() {
    translate([-body_w / 2, 0, base_t]) {
        color("BurlyWood") body();
        color("Wheat") front_plate();
        color("#2b2b2b") translate([board_x0, plate_t, board_z0]) {           // board, for checking
            translate([0, glass_t, 0]) cube([pcb_w, pcb_t, pcb_h]);
            translate([0, 0.6, pcb_h - glass_top - glass_h]) cube([pcb_w, glass_t - 0.6, glass_h]);
        }
        color("#58a6ff") translate([window_x0, plate_t - 0.1, window_z0]) cube([va_w, 0.3, va_h]);
    }
}
module assembly(gap = 0) {
    color("Peru") base();
    translate([0, -gap * 0.6, gap * 0.4]) body_assembled();
    translate([-body_w / 2, -gap * 0.6, base_t + body_h + gap * 0.9]) color("Sienna") collar();
    translate([0, head_y, base_t + body_h + 6 + gap * 1.3]) {
        color("BurlyWood") head_bottom();
        color("BurlyWood") translate([0, 0, gap * 0.5]) head_top();
        for (sx = [-1, 1]) color("SaddleBrown")
            translate([sx * (ear_x() + 0.5 + gap * 0.4), 0, ear_z])
                mirror([sx > 0 ? 1 : 0, 0, 0]) rotate([0, 0, 90]) rotate([90, 0, 0]) translate([0, 4, -ear_t]) ear();
    }
    color("SaddleBrown") translate([0, body_depth + 18 + gap * 0.5, base_t + 30 + 10]) rotate([90, 0, 90]) tail();
}

// ---------------------------------------------------------------- printable layouts (on the bed)
if (part == "assembly") assembly();
if (part == "exploded") assembly(gap = 35);
if (part == "front_plate") rotate([90, 0, 0]) front_plate();
if (part == "body") body();                                    // upright, floor on the bed
if (part == "head_top") translate([0, 0, -head_split_z]) head_top();
if (part == "head_bottom") translate([0, 0, head_split_z]) rotate([180, 0, 0]) head_bottom();
if (part == "ear_left") ear();
if (part == "ear_right") mirror([1, 0, 0]) ear();
if (part == "collar") translate([0, 0, 6]) rotate([180, 0, 0]) collar();
if (part == "base") base();
if (part == "tail") tail();
if (part == "neck_peg") neck_peg();
