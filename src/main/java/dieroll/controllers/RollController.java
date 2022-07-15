package dieroll.controllers;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.servlet.ModelAndView;

@Controller
public class RollController {

    @GetMapping("/rooms/{roomId}")
    public ModelAndView rooms(@PathVariable String roomId, Model model) {
        model.addAttribute("roomId", roomId);
        return new ModelAndView("room");
    }

}
